# services/sre-assistant/src/sre_assistant/tools/prometheus_tool.py
"""
Prometheus 查詢工具
用於查詢服務的關鍵指標（四大黃金訊號）
"""

import structlog
import httpx
import json
from typing import Dict, Any, Optional, List
from datetime import datetime, timezone
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception, RetryError

from ..contracts import ToolResult, ToolError

logger = structlog.get_logger(__name__)


def should_retry_prometheus_exception(exception: BaseException) -> bool:
    """
    決定是否應重試 Prometheus 請求的自訂邏輯。

    - 對於連線錯誤和超時，總是重試。
    - 對於 HTTP 狀態錯誤，僅對 5xx 系列的伺服器錯誤重試。
    - 對於其他錯誤（如 4xx 客戶端錯誤），不重試。
    """
    if isinstance(exception, (httpx.TimeoutException, httpx.ConnectError)):
        return True
    if isinstance(exception, httpx.HTTPStatusError):
        # 僅對 5xx (伺服器錯誤) 或 429 (請求過多) 重試
        return exception.response.status_code >= 500 or exception.response.status_code == 429
    return False


class PrometheusQueryTool:
    """
    Prometheus 查詢工具
    
    實作 SRE 四大黃金訊號查詢：
    - Latency (延遲)
    - Traffic (流量)
    - Errors (錯誤)
    - Saturation (飽和度)
    """
    
    def __init__(self, config, http_client: httpx.AsyncClient, redis_client=None):
        """
        初始化 Prometheus 工具

        Args:
            config: 應用程式設定物件。
            http_client: 一個共享的 httpx.AsyncClient 實例。
            redis_client: 非同步 Redis 客戶端，用於快取。
        """
        self.base_url = config.prometheus.base_url
        self.timeout = config.prometheus.timeout_seconds
        self.default_step = config.prometheus.default_step
        self.max_points = config.prometheus.max_points
        self.http_client = http_client
        
        # 快取設定
        self.redis_client = redis_client
        self.cache_ttl_seconds = config.prometheus.get("cache_ttl_seconds", 300) # 預設 5 分鐘

        # 重試設定
        self.max_retries = config.workflow.get("max_retries", 2)
        self.retry_wait_multiplier = config.workflow.get("retry_delay_seconds", 1)

        logger.info(
            f"✅ Prometheus 工具初始化 (使用共享 HTTP 客戶端): {self.base_url}",
            max_retries=self.max_retries,
            retry_wait_multiplier=self.retry_wait_multiplier
        )
    
    async def execute(self, params: Dict[str, Any]) -> ToolResult:
        """
        執行 Prometheus 查詢
        
        Args:
            params: 包含查詢參數的字典
                - service: 服務名稱
                - namespace: 命名空間
                - metric_type: 指標類型 (latency/traffic/errors/saturation)
                - time_range: 時間範圍（分鐘）
                
        Returns:
            ToolResult 包含查詢結果或錯誤
        """
        try:
            service = params.get("service", "")
            namespace = params.get("namespace", "default")
            metric_type = params.get("metric_type", "all")
            time_range = params.get("time_range", 30)  # 預設 30 分鐘
            
            logger.info(f"📊 查詢 Prometheus: service={service}, namespace={namespace}, type={metric_type}")
            
            # 優先處理自定義查詢
            query = params.get("query")
            if query:
                metrics = await self._query_custom(query, time_range)
            # 否則，根據指標類型執行查詢
            elif metric_type == "all":
                metrics = await self.query_golden_signals(service, namespace, time_range)
            elif metric_type == "latency":
                metrics = await self._query_latency(service, namespace, time_range)
            elif metric_type == "traffic":
                metrics = await self._query_traffic(service, namespace, time_range)
            elif metric_type == "errors":
                metrics = await self._query_errors(service, namespace, time_range)
            elif metric_type == "saturation":
                metrics = await self._query_saturation(service, namespace, time_range)
            else:
                # 保留一個後備，儘管在上面的邏輯中不太可能到達
                metrics = {"error": f"未知指標類型: {metric_type}"}
            
            return ToolResult(
                success=True,
                data=metrics,
                metadata={
                    "source": "prometheus",
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "query_time_range": f"{time_range}m"
                }
            )
            
        except RetryError as e:
            logger.error(f"❌ Prometheus API 查詢在重試後仍然失敗: {e}", exc_info=True)
            original_exception = e.last_attempt.exception()

            error_code = "RETRY_ERROR"
            error_message = "Request failed after multiple retries."
            details = {"last_exception": str(original_exception)}

            if isinstance(original_exception, httpx.HTTPStatusError):
                error_code = "HTTP_STATUS_ERROR"
                error_message = f"Prometheus API returned HTTP {original_exception.response.status_code}: {original_exception.response.reason_phrase}"
                details = {
                    "status_code": original_exception.response.status_code,
                    "response_body": original_exception.response.text[:500],
                    "request_url": str(original_exception.request.url),
                }
            elif isinstance(original_exception, httpx.TimeoutException):
                error_code = "TIMEOUT_ERROR"
                error_message = f"Prometheus API request timed out after {self.timeout}s"
                details = {
                    "timeout_seconds": self.timeout,
                    "request_url": str(original_exception.request.url) if hasattr(original_exception, 'request') else None,
                }
            elif isinstance(original_exception, httpx.ConnectError):
                error_code = "CONNECTION_ERROR"
                error_message = f"Failed to connect to Prometheus: {str(original_exception)}"
                details = {"base_url": self.base_url}

            details["params"] = params
            details["retries"] = self.max_retries

            return ToolResult(
                success=False,
                error=ToolError(code=error_code, message=error_message, details=details)
            )
        except httpx.HTTPStatusError as e:
            # 只有在 tenacity 不重試時 (例如 4xx 錯誤) 才會直接觸發這裡
            logger.error(f"❌ Prometheus API 查詢失敗 (非重試): {e.response.status_code} - {e.response.text}", exc_info=True)
            return ToolResult(
                success=False,
                error=ToolError(
                    code="HTTP_STATUS_ERROR",
                    message=f"Prometheus API returned HTTP {e.response.status_code}: {e.response.reason_phrase}",
                    details={
                        "status_code": e.response.status_code,
                        "response_body": e.response.text[:500],
                        "request_url": str(e.request.url),
                        "params": params
                    }
                )
            )
        except httpx.TimeoutException as e:
            logger.error(f"❌ Prometheus API 請求超時: {e}", exc_info=True)
            return ToolResult(
                success=False,
                error=ToolError(
                    code="TIMEOUT_ERROR",
                    message=f"Prometheus API request timed out after {self.timeout}s",
                    details={
                        "timeout_seconds": self.timeout,
                        "request_url": str(e.request.url) if hasattr(e, 'request') else None,
                        "params": params
                    }
                )
            )
        except httpx.ConnectError as e:
            logger.error(f"❌ Prometheus API 連線失敗: {e}", exc_info=True)
            return ToolResult(
                success=False,
                error=ToolError(
                    code="CONNECTION_ERROR",
                    message=f"Failed to connect to Prometheus: {str(e)}",
                    details={
                        "base_url": self.base_url,
                        "params": params
                    }
                )
            )
        except Exception as e:
            logger.error(f"❌ Prometheus 工具執行時發生未預期錯誤: {e}", exc_info=True)
            return ToolResult(
                success=False,
                error=ToolError(
                    code="UNEXPECTED_ERROR",
                    message=f"Unexpected error in Prometheus tool: {str(e)}",
                    details={
                        "error_type": type(e).__name__,
                        "params": params
                    }
                )
            )
    
    async def query_golden_signals(self, service_name: str, namespace: str, duration: str) -> Dict[str, Any]:
        """查詢四大黃金訊號"""
        results = {}
        
        # 並行查詢所有指標
        import asyncio
        tasks = [
            self._query_latency(service_name, namespace, duration),
            self._query_traffic(service_name, namespace, duration),
            self._query_errors(service_name, namespace, duration),
            self._query_saturation(service_name, namespace, duration)
        ]
        
        latency, traffic, errors, saturation = await asyncio.gather(*tasks, return_exceptions=True)
        
        # 處理結果
        if not isinstance(latency, Exception):
            results["latency"] = latency
        if not isinstance(traffic, Exception):
            results["traffic"] = traffic
        if not isinstance(errors, Exception):
            results["errors"] = errors
        if not isinstance(saturation, Exception):
            results["saturation"] = saturation
        
        return results
    
    async def _query_latency(self, service: str, namespace: str, time_range: int) -> Dict[str, Any]:
        """查詢延遲指標"""
        # P50, P95, P99 延遲
        queries = {
            "p50": f'histogram_quantile(0.50, rate(http_request_duration_seconds_bucket{{service="{service}", namespace="{namespace}"}}[5m]))',
            "p95": f'histogram_quantile(0.95, rate(http_request_duration_seconds_bucket{{service="{service}", namespace="{namespace}"}}[5m]))',
            "p99": f'histogram_quantile(0.99, rate(http_request_duration_seconds_bucket{{service="{service}", namespace="{namespace}"}}[5m]))'
        }
        
        results = {}
        for percentile, query in queries.items():
            value = await self._execute_instant_query(query)
            if value is not None:
                results[percentile] = f"{value*1000:.2f}ms"
        
        return results
    
    async def _query_traffic(self, service: str, namespace: str, time_range: int) -> Dict[str, Any]:
        """查詢流量指標"""
        # 請求率 (RPS)
        query = f'sum(rate(http_requests_total{{service="{service}", namespace="{namespace}"}}[5m]))'
        
        rps = await self._execute_instant_query(query)
        
        return {
            "requests_per_second": round(rps, 2) if rps else 0,
            "requests_per_minute": round(rps * 60, 2) if rps else 0
        }
    
    async def _query_errors(self, service: str, namespace: str, time_range: int) -> Dict[str, Any]:
        """查詢錯誤指標"""
        # 錯誤率
        error_query = f'sum(rate(http_requests_total{{service="{service}", namespace="{namespace}", status=~"5.."}}[5m]))'
        total_query = f'sum(rate(http_requests_total{{service="{service}", namespace="{namespace}"}}[5m]))'
        
        errors = await self._execute_instant_query(error_query)
        total = await self._execute_instant_query(total_query)
        
        error_rate = 0
        if total and total > 0:
            error_rate = (errors / total) * 100
        
        return {
            "error_rate": f"{error_rate:.2f}%",
            "errors_per_minute": round(errors * 60, 2) if errors else 0
        }
    
    async def _query_saturation(self, service: str, namespace: str, time_range: int) -> Dict[str, Any]:
        """查詢飽和度指標"""
        queries = {
            "cpu_usage": f'avg(rate(container_cpu_usage_seconds_total{{pod=~"{service}.*", namespace="{namespace}"}}[5m])) * 100',
            "memory_usage": f'avg(container_memory_usage_bytes{{pod=~"{service}.*", namespace="{namespace}"}}) / avg(container_spec_memory_limit_bytes{{pod=~"{service}.*", namespace="{namespace}"}}) * 100',
            "disk_usage": f'avg(container_fs_usage_bytes{{pod=~"{service}.*", namespace="{namespace}"}}) / avg(container_fs_limit_bytes{{pod=~"{service}.*", namespace="{namespace}"}}) * 100'
        }
        
        results = {}
        for metric, query in queries.items():
            value = await self._execute_instant_query(query)
            if value is not None:
                results[metric] = f"{value:.2f}%"
        
        # 查詢 Pod 數量
        pod_query = f'count(up{{job="{service}", namespace="{namespace}"}})'
        pod_count = await self._execute_instant_query(pod_query)
        results["pod_count"] = int(pod_count) if pod_count else 0
        
        return results
    
    async def _query_custom(self, query: str, time_range: int) -> Dict[str, Any]:
        """執行自定義查詢"""
        if not query:
            return {"error": "No query provided"}
        
        value = await self._execute_instant_query(query)
        return {"value": value, "query": query}
    
    async def check_health(self) -> bool:
        """
        執行對 Prometheus 的健康檢查。

        Returns:
            如果 Prometheus 可達且健康，則返回 True，否則返回 False。
        """
        try:
            response = await self.http_client.get(f"{self.base_url}/-/healthy", timeout=self.timeout)
            response.raise_for_status()
            logger.debug(f"Prometheus health check successful: {response.status_code}")
            return True
        except (httpx.HTTPStatusError, httpx.RequestError) as e:
            logger.warning(f"Prometheus health check failed: {e}")
            return False

    async def _execute_with_retry(self, request_func, **kwargs):
        """
        一個通用的包裝函式，以程式化的方式執行具有 tenacity 重試邏輯的請求。
        這允許我們使用來自 'self' 的配置 (例如 self.max_retries)。
        """
        retry_decorator = retry(
            stop=stop_after_attempt(self.max_retries + 1),
            wait=wait_exponential(multiplier=self.retry_wait_multiplier, min=2, max=10),
            retry=retry_if_exception(should_retry_prometheus_exception),
            reraise=True
        )
        return await retry_decorator(request_func)(**kwargs)

    async def _execute_instant_query(self, query: str) -> Optional[float]:
        """
        執行即時查詢，並增加 Redis 快取機制。
        """
        cache_key = f"prometheus:instant:{query}"

        if self.redis_client:
            try:
                cached_result = await self.redis_client.get(cache_key)
                if cached_result:
                    logger.info(f"CACHE HIT: 從 Redis 獲取即時查詢結果: {query}")
                    data = json.loads(cached_result)
                    return float(data) if data is not None else None
            except Exception as e:
                logger.error(f"Redis 快取讀取失敗: {e}")

        async def do_request():
            params = {"query": query, "time": datetime.now(timezone.utc).isoformat()}
            response = await self.http_client.get(
                f"{self.base_url}/api/v1/query",
                params=params,
                timeout=self.timeout
            )
            response.raise_for_status()
            return response.json()

        data = await self._execute_with_retry(do_request)

        if data["status"] != "success":
            logger.warning(f"Prometheus 查詢 '{query}' 成功執行但未返回 'success' 狀態: {data.get('error', 'Unknown error')}")
            return None

        value_to_cache = None
        results = data.get("data", {}).get("result", [])
        if results and len(results) > 0:
            value = results[0].get("value", [])
            if len(value) > 1:
                value_to_cache = float(value[1])

        if self.redis_client and value_to_cache is not None:
            try:
                await self.redis_client.set(
                    cache_key,
                    json.dumps(value_to_cache),
                    ex=self.cache_ttl_seconds,
                )
                logger.info(f"CACHE SET: 已快取即時查詢結果: {query}")
            except Exception as e:
                logger.error(f"Redis 快取寫入失敗: {e}")

        return value_to_cache
    
    async def _execute_range_query(self, query: str, start: datetime, end: datetime, step: str = "1m") -> List[Dict]:
        """
        執行範圍查詢，並增加 Redis 快取機制。
        """
        start_key = start.strftime('%Y-%m-%dT%H:%M')
        end_key = end.strftime('%Y-%m-%dT%H:%M')
        cache_key = f"prometheus:range:{query}:{start_key}:{end_key}:{step}"

        if self.redis_client:
            try:
                cached_result = await self.redis_client.get(cache_key)
                if cached_result:
                    logger.info(f"CACHE HIT: 從 Redis 獲取範圍查詢結果: {query}")
                    return json.loads(cached_result)
            except Exception as e:
                logger.error(f"Redis 快取讀取失敗: {e}")

        async def do_request():
            params = {
                "query": query,
                "start": start.isoformat(),
                "end": end.isoformat(),
                "step": step
            }
            response = await self.http_client.get(
                f"{self.base_url}/api/v1/query_range",
                params=params,
                timeout=self.timeout
            )
            response.raise_for_status()
            return response.json()

        data = await self._execute_with_retry(do_request)

        if data["status"] != "success":
            logger.warning(f"Prometheus 查詢 '{query}' 成功執行但未返回 'success' 狀態: {data.get('error', 'Unknown error')}")
            return []

        result_to_cache = data.get("data", {}).get("result", [])

        if self.redis_client and result_to_cache:
            try:
                await self.redis_client.set(
                    cache_key,
                    json.dumps(result_to_cache),
                    ex=self.cache_ttl_seconds,
                )
                logger.info(f"CACHE SET: 已快取範圍查詢結果: {query}")
            except Exception as e:
                logger.error(f"Redis 快取寫入失敗: {e}")

        return result_to_cache
