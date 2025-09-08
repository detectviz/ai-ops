# services/sre-assistant/src/sre_assistant/tools/control_plane_tool.py
"""
Control Plane 整合工具
用於回調 Control Plane API 獲取審計日誌和變更歷史
"""

import structlog
import httpx
from typing import Dict, Any, Optional
import jwt
import time

from pydantic import ValidationError

from ..contracts import ToolResult, ToolError
from .control_plane_contracts import (
    Resource, ResourceList, ResourceGroupList, AlertRuleList, ExecutionList,
    AuditLogList, IncidentList
)

logger = structlog.get_logger(__name__)


class ControlPlaneTool:
    """
    Control Plane API 整合工具
    """
    
    def __init__(self, config, http_client: httpx.AsyncClient):
        """初始化 Control Plane 工具"""
        self.base_url = config.control_plane.base_url
        self.timeout = config.control_plane.timeout_seconds
        self.http_client = http_client
        
        self.client_id = config.control_plane.client_id
        self.client_secret = config.control_plane.client_secret
        self.token_url = config.auth.keycloak.token_url
        self.token = None
        self.token_expires_at = 0
        
        logger.info(f"✅ Control Plane 工具初始化 (使用共享 HTTP 客戶端): {self.base_url}")

    async def check_health(self) -> bool:
        """
        執行對 Control Plane 的健康檢查。
        """
        try:
            response = await self._make_request(method="GET", endpoint="/api/v1/healthz")
            return response.get("status") == "healthy"
        except Exception as e:
            logger.warning(f"Control Plane health check failed: {e}")
            return False

    async def get_audit_logs(self, service_name: str, limit: int = 10) -> ToolResult:
        """
        查詢指定服務的審計日誌 (舊版端點，為相容性保留)
        """
        params = {"service_name": service_name, "limit": limit}
        try:
            logger.info(f"🛂 (ControlPlaneTool) 正在查詢 {service_name} 的審計日誌 (舊版)...")
            response_data = await self._make_request(method="GET", endpoint="/v1/audit-logs", params=params)
            return ToolResult(success=True, data={"logs": response_data.get("logs", [])})
        except Exception as e:
            return self._handle_error(e, params)

    async def query_resources(self, params: Optional[Dict] = None) -> ToolResult:
        """
        查詢資源狀態 (GET /api/v1/resources)
        """
        try:
            response_data = await self._make_request(method="GET", endpoint="/api/v1/resources", params=params)
            return ToolResult(success=True, data=ResourceList.model_validate(response_data).model_dump())
        except ValidationError as e:
            return self._handle_validation_error(e, params)
        except Exception as e:
            return self._handle_error(e, params)

    async def get_resource_details(self, resource_id: str) -> ToolResult:
        """
        獲取資源詳情 (GET /api/v1/resources/{resourceId})
        """
        params = {"resource_id": resource_id}
        try:
            response_data = await self._make_request(method="GET", endpoint=f"/api/v1/resources/{resource_id}")
            return ToolResult(success=True, data=Resource.model_validate(response_data).model_dump())
        except ValidationError as e:
            return self._handle_validation_error(e, params)
        except Exception as e:
            return self._handle_error(e, params)

    async def query_resource_groups(self, params: Optional[Dict] = None) -> ToolResult:
        """
        查詢資源群組 (GET /api/v1/resource-groups)
        """
        try:
            response_data = await self._make_request(method="GET", endpoint="/api/v1/resource-groups", params=params)
            return ToolResult(success=True, data=ResourceGroupList.model_validate(response_data).model_dump())
        except ValidationError as e:
            return self._handle_validation_error(e, params)
        except Exception as e:
            return self._handle_error(e, params)

    async def query_audit_logs(self, params: Optional[Dict] = None) -> ToolResult:
        """查詢部署相關的審計日誌 (GET /api/v1/audit-logs)"""
        try:
            response_data = await self._make_request(method="GET", endpoint="/api/v1/audit-logs", params=params)
            return ToolResult(success=True, data=AuditLogList.model_validate(response_data).model_dump())
        except ValidationError as e:
            return self._handle_validation_error(e, params)
        except Exception as e:
            return self._handle_error(e, params)

    async def query_incidents(self, params: Optional[Dict] = None) -> ToolResult:
        """查詢相關事件 (GET /api/v1/incidents)"""
        try:
            response_data = await self._make_request(method="GET", endpoint="/api/v1/incidents", params=params)
            return ToolResult(success=True, data=IncidentList.model_validate(response_data).model_dump())
        except ValidationError as e:
            return self._handle_validation_error(e, params)
        except Exception as e:
            return self._handle_error(e, params)

    async def get_alert_rules(self, params: Optional[Dict] = None) -> ToolResult:
        """
        獲取告警規則狀態 (GET /api/v1/alert-rules)
        """
        try:
            response_data = await self._make_request(method="GET", endpoint="/api/v1/alert-rules", params=params)
            return ToolResult(success=True, data=AlertRuleList.model_validate(response_data).model_dump())
        except ValidationError as e:
            return self._handle_validation_error(e, params)
        except Exception as e:
            return self._handle_error(e, params)

    async def query_automation_executions(self, params: Optional[Dict] = None) -> ToolResult:
        """
        查詢自動化腳本執行歷史 (GET /api/v1/automation/executions)
        """
        try:
            response_data = await self._make_request(method="GET", endpoint="/api/v1/automation/executions", params=params)
            return ToolResult(success=True, data=ExecutionList.model_validate(response_data).model_dump())
        except ValidationError as e:
            return self._handle_validation_error(e, params)
        except Exception as e:
            return self._handle_error(e, params)

    def _handle_error(self, e: Exception, params: Optional[Dict]) -> ToolResult:
        if isinstance(e, httpx.HTTPStatusError):
            code, msg = "HTTP_STATUS_ERROR", f"API returned HTTP {e.response.status_code}"
            details={"status_code": e.response.status_code, "response_body": e.response.text[:500], "request_url": str(e.request.url), "params": params}
        elif isinstance(e, httpx.TimeoutException):
            code, msg = "TIMEOUT_ERROR", "API request timed out"
            details={"timeout_seconds": self.timeout, "request_url": str(e.request.url), "params": params}
        elif isinstance(e, httpx.ConnectError):
            code, msg = "CONNECTION_ERROR", "Failed to connect to API"
            details={"base_url": self.base_url, "params": params}
        else:
            code, msg = "UNEXPECTED_ERROR", str(e)
            details={"error_type": type(e).__name__, "params": params}

        logger.error(f"❌ Control Plane 工具錯誤: {msg}", exc_info=True)
        return ToolResult(success=False, error=ToolError(code=code, message=msg, details=details))

    def _handle_validation_error(self, e: ValidationError, params: Optional[Dict]) -> ToolResult:
        logger.error(f"❌ Control Plane API 回應資料格式無效: {e}", exc_info=True)
        return ToolResult(success=False, error=ToolError(code="VALIDATION_ERROR", message="API response validation failed", details={"validation_errors": e.errors(), "params": params}))

    async def _get_auth_token(self) -> Optional[str]:
        """
        獲取或刷新 M2M 認證 Token
        """
        if self.token and self.token_expires_at > (time.time() + 60):
            return self.token

        logger.info("🔑 Token 過期或不存在，正在從 Keycloak 獲取新 Token...")
        try:
            data = {"client_id": self.client_id, "client_secret": self.client_secret, "grant_type": "client_credentials"}
            response = await self.http_client.post(self.token_url, data=data, timeout=self.timeout)

            if response.status_code != 200:
                logger.error(f"❌ 從 Keycloak 獲取 Token 失敗: {response.status_code} - {response.text}")
                return None

            token_data = response.json()
            self.token = token_data["access_token"]
            decoded_token = jwt.decode(self.token, options={"verify_signature": False})
            self.token_expires_at = decoded_token.get("exp", 0)
            logger.info("✅ 成功獲取並快取了新的 Token")
            return self.token
                
        except Exception as e:
            logger.error(f"❌ 獲取 Token 時發生嚴重錯誤: {e}")
            return None

    async def _make_request(self, method: str, endpoint: str, params: Optional[Dict] = None, json_data: Optional[Dict] = None) -> Dict[str, Any]:
        """
        向 Control Plane API 發送認證請求
        """
        token = await self._get_auth_token()
        if not token:
            raise Exception("無法獲取認證 Token")
            
        headers = {"Authorization": f"Bearer {token}"}
        url = f"{self.base_url}{endpoint}"
        
        response = await self.http_client.request(method, url, headers=headers, params=params, json=json_data, timeout=self.timeout)
        response.raise_for_status()
        return response.json()
