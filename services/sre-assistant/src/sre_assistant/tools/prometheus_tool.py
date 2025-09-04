# services/sre-assistant/src/sre_assistant/tools/prometheus_tool.py
"""
Prometheus 查詢工具
用於查詢服務的關鍵指標（四大黃金訊號）
"""

import logging
import httpx
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta, timezone
from urllib.parse import urlencode

from ..contracts import ToolResult, ToolError

logger = logging.getLogger(__name__)


class PrometheusQueryTool:
    """
    Prometheus 查詢工具
    
    實作 SRE 四大黃金訊號查詢：
    - Latency (延遲)
    - Traffic (流量)
    - Errors (錯誤)
    - Saturation (飽和度)
    """
    
    def __init__(self, config):
        """初始化 Prometheus 工具"""
        self.base_url = config.prometheus.get("base_url", "http://prometheus:9090")
        self.timeout = config.prometheus.get("timeout_seconds", 15)
        self.default_step = config.prometheus.get("default_step", "1m")
        self.max_points = config.prometheus.get("max_points", 1000)
        
        logger.info(f"✅ Prometheus 工具初始化: {self.base_url}")
    
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
            
            # 根據指標類型執行查詢
            if metric_type == "all":
                metrics = await self._query_golden_signals(service, namespace, time_range)
            elif metric_type == "latency":
                metrics = await self._query_latency(service, namespace, time_range)
            elif metric_type == "traffic":
                metrics = await self._query_traffic(service, namespace, time_range)
            elif metric_type == "errors":
                metrics = await self._query_errors(service, namespace, time_range)
            elif metric_type == "saturation":
                metrics = await self._query_saturation(service, namespace, time_range)
            else:
                metrics = await self._query_custom(params.get("query", ""), time_range)
            
            return ToolResult(
                success=True,
                data=metrics,
                metadata={
                    "source": "prometheus",
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "query_time_range": f"{time_range}m"
                }
            )
            
        except Exception as e:
            logger.error(f"❌ Prometheus 查詢失敗: {e}")
            return ToolResult(
                success=False,
                error=ToolError(
                    code="PROMETHEUS_QUERY_ERROR",
                    message=str(e),
                    details={"params": params}
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
    
    async def _execute_instant_query(self, query: str) -> Optional[float]:
        """
        執行即時查詢
        
        Args:
            query: PromQL 查詢語句
            
        Returns:
            查詢結果的數值，如果無結果則返回 None
        """
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                params = {
                    "query": query,
                    "time": datetime.now(timezone.utc).isoformat()
                }
                
                response = await client.get(
                    f"{self.base_url}/api/v1/query",
                    params=params
                )
                
                if response.status_code != 200:
                    logger.error(f"Prometheus 回應錯誤: {response.status_code}")
                    return None
                
                data = response.json()
                
                if data["status"] != "success":
                    logger.error(f"查詢失敗: {data.get('error', 'Unknown error')}")
                    return None
                
                # 提取第一個結果的值
                results = data.get("data", {}).get("result", [])
                if results and len(results) > 0:
                    value = results[0].get("value", [])
                    if len(value) > 1:
                        return float(value[1])
                
                return None
                
        except Exception as e:
            logger.error(f"執行查詢時發生錯誤: {e}")
            return None
    
    async def _execute_range_query(self, query: str, start: datetime, end: datetime, step: str = "1m") -> List[Dict]:
        """
        執行範圍查詢
        
        Args:
            query: PromQL 查詢語句
            start: 開始時間
            end: 結束時間
            step: 步長
            
        Returns:
            時間序列數據列表
        """
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                params = {
                    "query": query,
                    "start": start.isoformat(),
                    "end": end.isoformat(),
                    "step": step
                }
                
                response = await client.get(
                    f"{self.base_url}/api/v1/query_range",
                    params=params
                )
                
                if response.status_code != 200:
                    logger.error(f"Prometheus 回應錯誤: {response.status_code}")
                    return []
                
                data = response.json()
                
                if data["status"] != "success":
                    logger.error(f"查詢失敗: {data.get('error', 'Unknown error')}")
                    return []
                
                return data.get("data", {}).get("result", [])
                
        except Exception as e:
            logger.error(f"執行範圍查詢時發生錯誤: {e}")
            return []