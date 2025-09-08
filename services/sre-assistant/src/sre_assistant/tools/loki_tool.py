# services/sre-assistant/src/sre_assistant/tools/loki_tool.py
"""
Loki 日誌查詢工具
用於查詢和分析服務日誌
"""

import asyncio
import structlog
import httpx
import json
import re
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta, timezone

from ..contracts import ToolResult, ToolError

logger = structlog.get_logger(__name__)


class LokiLogQueryTool:
    """
    Loki 日誌查詢工具
    """
    
    def __init__(self, config, http_client: httpx.AsyncClient):
        """初始化 Loki 工具"""
        self.base_url = config.loki.base_url
        self.timeout = config.loki.timeout_seconds
        self.default_limit = config.loki.default_limit
        self.max_time_range = config.loki.max_time_range
        self.http_client = http_client
        
        logger.info(f"✅ Loki 工具初始化 (使用共享 HTTP 客戶端): {self.base_url}")

    async def check_health(self) -> bool:
        """
        執行對 Loki 的健康檢查。
        """
        try:
            response = await self.http_client.get(f"{self.base_url}/ready", timeout=self.timeout)
            response.raise_for_status()
            if response.text.strip() == "ready":
                logger.debug(f"Loki health check successful: {response.status_code}")
                return True
            logger.warning(f"Loki health check response is not 'ready': {response.text}")
            return False
        except (httpx.HTTPStatusError, httpx.RequestError) as e:
            logger.warning(f"Loki health check failed: {e}")
            return False
    
    async def execute(self, params: Dict[str, Any]) -> ToolResult:
        """
        執行 Loki 日誌查詢
        """
        try:
            service = params.get("service", "")
            namespace = params.get("namespace", "default")
            log_level = params.get("log_level", "error")
            pattern = params.get("pattern", "")
            time_range = params.get("time_range", 30)
            limit = params.get("limit", self.default_limit)
            
            logger.info(f"📝 查詢 Loki: service={service}, level={log_level}, pattern={pattern}")
            
            logs = await self._query_logs(service, namespace, log_level, pattern, time_range, limit)
            analysis = self._analyze_logs(logs)
            
            return ToolResult(
                success=True,
                data={"logs": logs, "analysis": analysis, "query_params": {"service": service, "namespace": namespace, "log_level": log_level, "time_range": f"{time_range}m"}},
                metadata={"source": "loki", "timestamp": datetime.now(timezone.utc).isoformat(), "total_logs": len(logs)}
            )
            
        except httpx.HTTPStatusError as e:
            return self._handle_error(e, params)
        except httpx.TimeoutException as e:
            return self._handle_error(e, params)
        except httpx.ConnectError as e:
            return self._handle_error(e, params)
        except Exception as e:
            return self._handle_error(e, params)
    
    def _handle_error(self, e: Exception, params: Optional[Dict]) -> ToolResult:
        if isinstance(e, httpx.HTTPStatusError):
            logger.error(f"❌ Loki API 查詢失敗: {e.response.status_code} - {e.response.text}", exc_info=True)
            return ToolResult(success=False, error=ToolError(code="HTTP_STATUS_ERROR", message=f"Loki API returned HTTP {e.response.status_code}", details={"status_code": e.response.status_code, "response_body": e.response.text[:500], "request_url": str(e.request.url), "params": params}))
        if isinstance(e, httpx.TimeoutException):
            logger.error(f"❌ Loki API 請求超時: {e}", exc_info=True)
            return ToolResult(success=False, error=ToolError(code="TIMEOUT_ERROR", message=f"Loki API request timed out", details={"timeout_seconds": self.timeout, "request_url": str(e.request.url), "params": params}))
        if isinstance(e, httpx.ConnectError):
            logger.error(f"❌ Loki API 連線失敗: {e}", exc_info=True)
            return ToolResult(success=False, error=ToolError(code="CONNECTION_ERROR", message="Failed to connect to Loki", details={"base_url": self.base_url, "params": params}))
        
        logger.error(f"❌ Loki 工具執行時發生未預期錯誤: {e}", exc_info=True)
        return ToolResult(success=False, error=ToolError(code="UNEXPECTED_ERROR", message=str(e), details={"error_type": type(e).__name__, "params": params}))

    async def _query_logs(self, service: str, namespace: str, log_level: str, pattern: str, time_range: int, limit: int) -> List[Dict[str, Any]]:
        """
        查詢日誌
        """
        query = self._build_logql_query(service, namespace, log_level, pattern)
        end_time = datetime.now(timezone.utc)
        start_time = end_time - timedelta(minutes=time_range)
        
        params = {
            "query": query,
            "start": str(int(start_time.timestamp() * 1e9)),
            "end": str(int(end_time.timestamp() * 1e9)),
            "limit": limit,
            "direction": "backward"
        }

        response = await self.http_client.get(f"{self.base_url}/loki/api/v1/query_range", params=params, timeout=self.timeout)
        response.raise_for_status()
        data = response.json()

        if data.get("status") != "success":
            error_msg = data.get('error', 'Unknown Loki query error')
            logger.warning(f"Loki 查詢成功但語法或執行失敗: {error_msg}")
            return []

        return self._parse_log_results(data.get("data", {}).get("result", []))
    
    def _build_logql_query(self, service: str, namespace: str, log_level: str, pattern: str) -> str:
        """
        建構 LogQL 查詢語句
        """
        selectors = []
        if service: selectors.append(f'app="{service}"')
        if namespace: selectors.append(f'namespace="{namespace}"')
        if not selectors: selectors.append('job=~".+"')
        query = "{" + ",".join(selectors) + "}"
        
        if log_level and log_level.lower() != "all":
            level_patterns = {
                "error": "(?i)(error|err|fatal|panic|critical)",
                "warn": "(?i)(warn|warning)",
                "info": "(?i)(info|information)",
                "debug": "(?i)(debug|trace)"
            }
            if log_level.lower() in level_patterns:
                query += f' |~ "{level_patterns[log_level.lower()]}"'
        
        if pattern: query += f' |~ "{pattern}"'
        return query
    
    def _parse_log_results(self, results: List[Dict]) -> List[Dict[str, Any]]:
        """
        解析 Loki 查詢結果
        """
        logs = []
        for stream in results:
            stream_labels = stream.get("stream", {})
            for value in stream.get("values", []):
                if len(value) >= 2:
                    logs.append({
                        "timestamp": datetime.fromtimestamp(int(value[0]) / 1e9, tz=timezone.utc).isoformat(),
                        "labels": stream_labels,
                        "message": value[1],
                        "parsed": self._parse_log_line(value[1])
                    })
        logs.sort(key=lambda x: x["timestamp"], reverse=True)
        return logs
    
    def _parse_log_line(self, log_line: str) -> Dict[str, Any]:
        """
        解析單行日誌
        """
        try:
            return json.loads(log_line)
        except json.JSONDecodeError:
            return {"raw": log_line, "level": self._extract_log_level(log_line), "error_type": self._extract_error_type(log_line)}
    
    def _extract_log_level(self, log_line: str) -> str:
        """提取日誌級別"""
        log_line_lower = log_line.lower()
        if any(word in log_line_lower for word in ["error", "err", "fatal", "panic", "critical"]): return "ERROR"
        if any(word in log_line_lower for word in ["warn", "warning"]): return "WARN"
        if any(word in log_line_lower for word in ["info", "information"]): return "INFO"
        if any(word in log_line_lower for word in ["debug", "trace"]): return "DEBUG"
        return "UNKNOWN"
    
    def _extract_error_type(self, log_line: str) -> Optional[str]:
        """提取錯誤類型"""
        error_patterns = {"OOMKilled": "記憶體不足", "Connection refused": "連接被拒絕", "Connection timeout": "連接超時", "NullPointerException": "空指標異常", "StackOverflowError": "堆疊溢出", "OutOfMemoryError": "記憶體不足", "DeadlockDetected": "死鎖偵測", "Circuit breaker": "熔斷器觸發", "Rate limit": "速率限制", "401": "未授權", "403": "禁止訪問", "404": "資源未找到", "500": "內部伺服器錯誤", "502": "閘道錯誤", "503": "服務不可用", "504": "閘道超時"}
        for pattern, error_type in error_patterns.items():
            if pattern in log_line: return error_type
        return None
    
    def _analyze_logs(self, logs: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        分析日誌模式和統計
        """
        if not logs: return {"total_logs": 0, "level_distribution": {}, "error_types": {}, "top_errors": []}
        
        level_counts, error_types, error_messages = {}, {}, []
        for log in logs:
            level = log.get("parsed", {}).get("level", "UNKNOWN")
            level_counts[level] = level_counts.get(level, 0) + 1
            error_type = log.get("parsed", {}).get("error_type")
            if error_type: error_types[error_type] = error_types.get(error_type, 0) + 1
            if level == "ERROR": error_messages.append(log.get("message", ""))
        
        top_errors = []
        if error_messages:
            error_clusters = self._cluster_errors(error_messages)
            top_errors = sorted(error_clusters.items(), key=lambda x: x[1], reverse=True)[:5]
        
        return {"total_logs": len(logs), "level_distribution": level_counts, "error_types": error_types, "top_errors": [{"pattern": pattern, "count": count} for pattern, count in top_errors], "critical_indicators": self._identify_critical_indicators(logs)}
    
    def _cluster_errors(self, error_messages: List[str]) -> Dict[str, int]:
        """
        簡單的錯誤聚類
        """
        clusters = {}
        for message in error_messages:
            key_parts = []
            exception_words = re.findall(r'\b\w*Exception\b', message)
            if exception_words: key_parts.append(max(exception_words, key=len))
            error_codes = re.findall(r'\b[4-5]\d{2}\b', message)
            if error_codes: key_parts.extend(error_codes)
            if not key_parts: key_parts.append(message.splitlines()[0][:50])
            cluster_key = " | ".join(sorted(list(set(key_parts))))
            clusters[cluster_key] = clusters.get(cluster_key, 0) + 1
        return clusters
    
    def _identify_critical_indicators(self, logs: List[Dict[str, Any]]) -> List[str]:
        """
        識別關鍵指標
        """
        indicators = []
        if sum(1 for log in logs if "OOMKilled" in log.get("message", "")) > 0: indicators.append(f"發現 {sum(1 for log in logs if 'OOMKilled' in log.get('message', ''))} 次記憶體不足錯誤 (OOMKilled)")
        if sum(1 for log in logs if "panic" in log.get("message", "").lower()) > 0: indicators.append(f"發現 {sum(1 for log in logs if 'panic' in log.get('message', '').lower())} 次 Panic 錯誤")
        conn_errors = sum(1 for log in logs if any(p in log.get("message", "") for p in ["Connection refused", "Connection timeout", "connection reset"]))
        if conn_errors > 5: indicators.append(f"發現 {conn_errors} 次連接錯誤，可能存在網路問題")
        error_logs = sum(1 for log in logs if log.get("parsed", {}).get("level") == "ERROR")
        if len(logs) > 0 and (error_logs / len(logs)) * 100 > 50: indicators.append(f"錯誤率過高: {(error_logs / len(logs)) * 100:.1f}%")
        return indicators
