# services/sre-assistant/src/sre_assistant/tools/loki_tool.py
"""
Loki 日誌查詢工具
用於查詢和分析服務日誌
"""

import logging
import httpx
import json
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta, timezone
from urllib.parse import quote

from ..contracts import ToolResult, ToolError

logger = logging.getLogger(__name__)


class LokiLogQueryTool:
    """
    Loki 日誌查詢工具
    
    功能：
    - 查詢錯誤日誌
    - 分析日誌模式
    - 統計日誌級別分佈
    - 提取關鍵錯誤訊息
    """
    
    def __init__(self, config):
        """初始化 Loki 工具"""
        self.base_url = config.loki.base_url
        self.timeout = config.loki.timeout_seconds
        self.default_limit = config.loki.default_limit
        self.max_time_range = config.loki.max_time_range
        
        logger.info(f"✅ Loki 工具初始化: {self.base_url}")
    
    async def execute(self, params: Dict[str, Any]) -> ToolResult:
        """
        執行 Loki 日誌查詢
        
        Args:
            params: 查詢參數
                - service: 服務名稱
                - namespace: 命名空間
                - log_level: 日誌級別 (error/warn/info/debug)
                - pattern: 搜尋模式
                - time_range: 時間範圍（分鐘）
                - limit: 返回筆數限制
                
        Returns:
            ToolResult 包含查詢結果
        """
        try:
            service = params.get("service", "")
            namespace = params.get("namespace", "default")
            log_level = params.get("log_level", "error")
            pattern = params.get("pattern", "")
            time_range = params.get("time_range", 30)  # 預設 30 分鐘
            limit = params.get("limit", self.default_limit)
            
            logger.info(f"📝 查詢 Loki: service={service}, level={log_level}, pattern={pattern}")
            
            # 執行查詢
            logs = await self._query_logs(
                service=service,
                namespace=namespace,
                log_level=log_level,
                pattern=pattern,
                time_range=time_range,
                limit=limit
            )
            
            # 分析日誌
            analysis = self._analyze_logs(logs)
            
            return ToolResult(
                success=True,
                data={
                    "logs": logs,
                    "analysis": analysis,
                    "query_params": {
                        "service": service,
                        "namespace": namespace,
                        "log_level": log_level,
                        "time_range": f"{time_range}m"
                    }
                },
                metadata={
                    "source": "loki",
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "total_logs": len(logs)
                }
            )
            
        except httpx.HTTPStatusError as e:
            logger.error(f"❌ Loki API 查詢失敗: {e.response.status_code} - {e.response.text}", exc_info=True)
            return ToolResult(
                success=False,
                error=ToolError(
                    code="HTTP_STATUS_ERROR",
                    message=f"Loki API returned HTTP {e.response.status_code}: {e.response.reason_phrase}",
                    details={
                        "status_code": e.response.status_code,
                        "response_body": e.response.text[:500],  # 限制回應內容長度
                        "request_url": str(e.request.url),
                        "params": params
                    }
                )
            )
        except httpx.TimeoutException as e:
            logger.error(f"❌ Loki API 請求超時: {e}", exc_info=True)
            return ToolResult(
                success=False,
                error=ToolError(
                    code="TIMEOUT_ERROR",
                    message=f"Loki API request timed out after {self.timeout}s",
                    details={
                        "timeout_seconds": self.timeout,
                        "request_url": str(e.request.url) if hasattr(e, 'request') else None,
                        "params": params
                    }
                )
            )
        except httpx.ConnectError as e:
            logger.error(f"❌ Loki API 連線失敗: {e}", exc_info=True)
            return ToolResult(
                success=False,
                error=ToolError(
                    code="CONNECTION_ERROR",
                    message=f"Failed to connect to Loki: {str(e)}",
                    details={
                        "base_url": self.base_url,
                        "params": params
                    }
                )
            )
        except Exception as e:
            logger.error(f"❌ Loki 工具執行時發生未預期錯誤: {e}", exc_info=True)
            return ToolResult(
                success=False,
                error=ToolError(
                    code="UNEXPECTED_ERROR",
                    message=f"Unexpected error in Loki tool: {str(e)}",
                    details={
                        "error_type": type(e).__name__,
                        "params": params
                    }
                )
            )
    
    async def query_logs_by_service(
        self,
        service_name: str,
        namespace: str,
        level: str,
        duration: str
    ) -> Dict[str, Any]:
        """
        根據服務查詢和分析日誌
        
        Args:
            service_name: 服務名稱
            namespace: 命名空間
            level: 日誌級別
            duration: 時間範圍 (e.g., "5m", "1h")
            
        Returns:
            日誌分析結果
        """
        # 解析時間範圍
        import re
        time_value = int(re.search(r'\d+', duration).group())
        time_unit = re.search(r'[a-zA-Z]+', duration).group()
        
        if time_unit == "m":
            time_range_minutes = time_value
        elif time_unit == "h":
            time_range_minutes = time_value * 60
        else:
            time_range_minutes = 5 # 預設

        logs = await self._query_logs(
            service=service_name,
            namespace=namespace,
            log_level=level,
            pattern="", # 暫不使用
            time_range=time_range_minutes,
            limit=self.default_limit
        )
        
        return self._analyze_logs(logs)

    async def _query_logs(
        self,
        service: str,
        namespace: str,
        log_level: str,
        pattern: str,
        time_range: int,
        limit: int
    ) -> List[Dict[str, Any]]:
        """
        查詢日誌
        
        Returns:
            日誌列表
        """
        # 建構 LogQL 查詢
        query = self._build_logql_query(service, namespace, log_level, pattern)
        
        # 計算時間範圍
        end_time = datetime.now(timezone.utc)
        start_time = end_time - timedelta(minutes=time_range)
        
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            params = {
                "query": query,
                "start": str(int(start_time.timestamp() * 1e9)),  # 奈秒
                "end": str(int(end_time.timestamp() * 1e9)),
                "limit": limit,
                "direction": "backward"  # 最新的日誌優先
            }
            
            response = await client.get(
                f"{self.base_url}/loki/api/v1/query_range",
                params=params
            )
            
            # 讓上層的 execute 方法來處理 HTTP 錯誤
            response.raise_for_status()
            
            data = response.json()
            
            if data.get("status") != "success":
                # Loki 查詢本身可能失敗 (例如語法錯誤)
                error_msg = data.get('error', 'Unknown Loki query error')
                logger.warning(f"Loki 查詢成功但語法或執行失敗: {error_msg}")
                # 這種情況下也返回空列表，因為它是一個有效的“無結果”場景
                return []
            
            # 解析日誌
            return self._parse_log_results(data.get("data", {}).get("result", []))
    
    def _build_logql_query(self, service: str, namespace: str, log_level: str, pattern: str) -> str:
        """
        建構 LogQL 查詢語句
        
        Returns:
            LogQL 查詢字串
        """
        # 基本標籤選擇器
        selectors = []
        
        if service:
            selectors.append(f'app="{service}"')
        if namespace:
            selectors.append(f'namespace="{namespace}"')
        
        # 如果沒有任何選擇器，使用預設
        if not selectors:
            selectors.append('job=~".+"')
        
        query = "{" + ",".join(selectors) + "}"
        
        # 加入日誌級別過濾
        if log_level and log_level.lower() != "all":
            level_patterns = {
                "error": "(?i)(error|err|fatal|panic|critical)",
                "warn": "(?i)(warn|warning)",
                "info": "(?i)(info|information)",
                "debug": "(?i)(debug|trace)"
            }
            if log_level.lower() in level_patterns:
                query += f' |~ "{level_patterns[log_level.lower()]}"'
        
        # 加入自定義模式
        if pattern:
            query += f' |~ "{pattern}"'
        
        return query
    
    def _parse_log_results(self, results: List[Dict]) -> List[Dict[str, Any]]:
        """
        解析 Loki 查詢結果
        
        Returns:
            解析後的日誌列表
        """
        logs = []
        
        for stream in results:
            stream_labels = stream.get("stream", {})
            values = stream.get("values", [])
            
            for value in values:
                if len(value) >= 2:
                    timestamp_ns = int(value[0])
                    log_line = value[1]
                    
                    # 解析日誌內容
                    parsed_log = self._parse_log_line(log_line)
                    
                    logs.append({
                        "timestamp": datetime.fromtimestamp(timestamp_ns / 1e9, tz=timezone.utc).isoformat(),
                        "labels": stream_labels,
                        "message": log_line,
                        "parsed": parsed_log
                    })
        
        # 按時間排序（最新優先）
        logs.sort(key=lambda x: x["timestamp"], reverse=True)
        
        return logs
    
    def _parse_log_line(self, log_line: str) -> Dict[str, Any]:
        """
        解析單行日誌
        
        嘗試解析 JSON 格式，否則返回純文字
        """
        # 嘗試解析 JSON
        try:
            return json.loads(log_line)
        except json.JSONDecodeError:
            pass
        
        # 嘗試解析常見的日誌格式
        parsed = {
            "raw": log_line,
            "level": self._extract_log_level(log_line),
            "error_type": self._extract_error_type(log_line)
        }
        
        return parsed
    
    def _extract_log_level(self, log_line: str) -> str:
        """提取日誌級別"""
        log_line_lower = log_line.lower()
        
        if any(word in log_line_lower for word in ["error", "err", "fatal", "panic", "critical"]):
            return "ERROR"
        elif any(word in log_line_lower for word in ["warn", "warning"]):
            return "WARN"
        elif any(word in log_line_lower for word in ["info", "information"]):
            return "INFO"
        elif any(word in log_line_lower for word in ["debug", "trace"]):
            return "DEBUG"
        
        return "UNKNOWN"
    
    def _extract_error_type(self, log_line: str) -> Optional[str]:
        """提取錯誤類型"""
        # 常見錯誤模式
        error_patterns = {
            "OOMKilled": "記憶體不足",
            "Connection refused": "連接被拒絕",
            "Connection timeout": "連接超時",
            "NullPointerException": "空指標異常",
            "StackOverflowError": "堆疊溢出",
            "OutOfMemoryError": "記憶體不足",
            "DeadlockDetected": "死鎖偵測",
            "Circuit breaker": "熔斷器觸發",
            "Rate limit": "速率限制",
            "401": "未授權",
            "403": "禁止訪問",
            "404": "資源未找到",
            "500": "內部伺服器錯誤",
            "502": "閘道錯誤",
            "503": "服務不可用",
            "504": "閘道超時"
        }
        
        for pattern, error_type in error_patterns.items():
            if pattern in log_line:
                return error_type
        
        return None
    
    def _analyze_logs(self, logs: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        分析日誌模式和統計
        
        Returns:
            分析結果
        """
        if not logs:
            return {
                "total_logs": 0,
                "level_distribution": {},
                "error_types": {},
                "top_errors": []
            }
        
        # 統計日誌級別分佈
        level_counts = {}
        error_types = {}
        error_messages = []
        
        for log in logs:
            # 統計級別
            level = log.get("parsed", {}).get("level", "UNKNOWN")
            level_counts[level] = level_counts.get(level, 0) + 1
            
            # 統計錯誤類型
            error_type = log.get("parsed", {}).get("error_type")
            if error_type:
                error_types[error_type] = error_types.get(error_type, 0) + 1
            
            # 收集錯誤訊息
            if level == "ERROR":
                error_messages.append(log.get("message", ""))
        
        # 找出最常見的錯誤
        top_errors = []
        if error_messages:
            # 簡單的錯誤聚類（基於相似度）
            error_clusters = self._cluster_errors(error_messages)
            top_errors = sorted(error_clusters.items(), key=lambda x: x[1], reverse=True)[:5]
        
        return {
            "total_logs": len(logs),
            "level_distribution": level_counts,
            "error_types": error_types,
            "top_errors": [{"pattern": pattern, "count": count} for pattern, count in top_errors],
            "critical_indicators": self._identify_critical_indicators(logs)
        }
    
    def _cluster_errors(self, error_messages: List[str]) -> Dict[str, int]:
        """
        簡單的錯誤聚類
        
        基於關鍵詞提取相似錯誤
        """
        clusters = {}
        
        for message in error_messages:
            # 提取關鍵詞（簡化版本）
            key_parts = []
            
            # 尋找異常類型
            if "Exception" in message:
                exception_start = message.find("Exception")
                exception_end = message.find(" ", exception_start)
                if exception_end == -1:
                    exception_end = len(message)
                key_parts.append(message[exception_start:exception_end])
            
            # 尋找錯誤代碼
            import re
            error_codes = re.findall(r'\b[4-5]\d{2}\b', message)
            if error_codes:
                key_parts.extend(error_codes)
            
            # 如果沒有找到特定模式，使用前 50 個字元
            if not key_parts:
                key_parts.append(message[:50])
            
            cluster_key = " | ".join(key_parts)
            clusters[cluster_key] = clusters.get(cluster_key, 0) + 1
        
        return clusters
    
    def _identify_critical_indicators(self, logs: List[Dict[str, Any]]) -> List[str]:
        """
        識別關鍵指標
        
        Returns:
            關鍵問題指標列表
        """
        indicators = []
        
        # 檢查是否有 OOM
        oom_count = sum(1 for log in logs if "OOMKilled" in log.get("message", ""))
        if oom_count > 0:
            indicators.append(f"發現 {oom_count} 次記憶體不足錯誤 (OOMKilled)")
        
        # 檢查是否有 Panic
        panic_count = sum(1 for log in logs if "panic" in log.get("message", "").lower())
        if panic_count > 0:
            indicators.append(f"發現 {panic_count} 次 Panic 錯誤")
        
        # 檢查連接錯誤
        conn_errors = sum(1 for log in logs if any(
            pattern in log.get("message", "")
            for pattern in ["Connection refused", "Connection timeout", "connection reset"]
        ))
        if conn_errors > 5:
            indicators.append(f"發現 {conn_errors} 次連接錯誤，可能存在網路問題")
        
        # 檢查錯誤率
        error_logs = sum(1 for log in logs if log.get("parsed", {}).get("level") == "ERROR")
        if len(logs) > 0:
            error_rate = (error_logs / len(logs)) * 100
            if error_rate > 50:
                indicators.append(f"錯誤率過高: {error_rate:.1f}%")
        
        return indicators

    # --- Roadmap Task 1.3: Log Aggregation ---

    async def _execute_aggregation_query(self, query: str, time_range: int) -> int:
        """
        執行 Loki 聚合查詢 (如 count_over_time)。

        Args:
            query: 完整的 LogQL 聚合查詢語句。
            time_range: 查詢的時間範圍（分鐘）。

        Returns:
            聚合後的計數，失敗則返回 0。
        """
        end_time = datetime.now(timezone.utc)
        start_time = end_time - timedelta(minutes=time_range)

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                params = {
                    "query": query,
                    "start": str(int(start_time.timestamp() * 1e9)),
                    "end": str(int(end_time.timestamp() * 1e9)),
                    "step": f"{time_range}m" # 使用整個範圍作為單一步長
                }
                response = await client.get(f"{self.base_url}/loki/api/v1/query", params=params)
                response.raise_for_status()
                data = response.json()

                if data.get("status") != "success":
                    logger.warning(f"Loki 聚合查詢失敗: {data.get('error', 'Unknown error')}")
                    return 0

                result = data.get("data", {}).get("result", [])
                if result and result[0] and len(result[0].get("value", [])) > 1:
                    return int(result[0]["value"][1])
                return 0
        except httpx.HTTPStatusError as e:
            logger.error(f"執行聚合查詢時發生 HTTP 錯誤: {e.response.status_code}")
            return 0
        except Exception as e:
            logger.error(f"執行聚合查詢時發生未知錯誤: {e}", exc_info=True)
            return 0

    async def aggregate_logs_by_level(
        self, service: str, namespace: str, time_range: int
    ) -> Dict[str, int]:
        """
        使用 LogQL 在伺服器端按日誌級別聚合日誌數量。

        這是一個探索性功能，用於與客戶端分析進行比較。
        它透過為每個級別執行並行的 count_over_time 查詢來工作。
        """
        logger.info(f"🧪 執行 Loki 伺服器端日誌聚合: service={service}, time_range={time_range}m")

        base_selector = "{" + f'app="{service}",namespace="{namespace}"' + "}"
        time_filter = f"[{time_range}m]"

        level_patterns = {
            "error": '(?i)(error|err|fatal|panic|critical)',
            "warn": '(?i)(warn|warning)',
            "info": '(?i)(info|information)',
        }

        tasks = {}
        for level, pattern in level_patterns.items():
            # LogQL for count_over_time with a filter
            query = f"count_over_time({base_selector} |~ `{pattern}` {time_filter})"
            tasks[level] = self._execute_aggregation_query(query, time_range)

        # 並行執行所有聚合查詢
        results = await asyncio.gather(*tasks.values())

        # 將結果與級別名稱對應起來
        level_counts = {level: count for level, count in zip(tasks.keys(), results)}

        logger.info(f"📊 Loki 伺服器端聚合結果: {level_counts}")
        return level_counts