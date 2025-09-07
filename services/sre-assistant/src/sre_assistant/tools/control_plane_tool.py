# services/sre-assistant/src/sre_assistant/tools/control_plane_tool.py
"""
Control Plane 整合工具
用於回調 Control Plane API 獲取審計日誌和變更歷史
"""

import structlog
import httpx
from typing import Dict, Any, Optional, List, Union
from datetime import datetime, timedelta, timezone
import jwt
import time

from pydantic import ValidationError

from ..contracts import ToolResult, ToolError
from .control_plane_contracts import (
    Resource, ResourceList, ResourceGroupList, AlertRuleList, ExecutionList
)

logger = structlog.get_logger(__name__)


class ControlPlaneTool:
    """
    Control Plane API 整合工具
    
    功能：
    - 查詢審計日誌
    - 獲取服務變更歷史
    - 查詢告警事件
    - 獲取自動化執行紀錄
    """
    
    def __init__(self, config):
        """初始化 Control Plane 工具"""
        self.base_url = config.control_plane.base_url
        self.timeout = config.control_plane.timeout_seconds
        
        # M2M 認證設定
        self.client_id = config.control_plane.client_id
        self.client_secret = config.control_plane.client_secret
        self.token_url = config.auth.keycloak.token_url
        self.token = None  # JWT token 快取
        self.token_expires_at = 0  # token 到期時間
        
        logger.info(f"✅ Control Plane 工具初始化: {self.base_url}")

    async def check_health(self) -> bool:
        """
        執行對 Control Plane 的健康檢查。

        Returns:
            如果 Control Plane 可達且健康，則返回 True，否則返回 False。
        """
        try:
            # 複用 _make_request 以自動處理認證
            # 注意：Control Plane 的健康檢查端點可能不需要認證，
            # 但使用此方法可以確保一致性，並在未來需要時無縫接軌。
            response = await self._make_request(method="GET", endpoint="/api/v1/healthz")
            # 根據 Go 服務的慣例，健康的響應應該包含 'status': 'healthy'
            if response.get("status") == "healthy":
                logger.debug("Control Plane health check successful.")
                return True
            logger.warning(f"Control Plane health check response is not healthy: {response}")
            return False
        except Exception as e:
            # _make_request 已經記錄了詳細錯誤，這裡只需記錄檢查失敗即可
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
        except httpx.HTTPStatusError as e:
            logger.error(f"❌ Control Plane API 查詢審計日誌失敗: {e.response.status_code} - {e.response.text}", exc_info=True)
            return ToolResult(success=False, error=ToolError(code="HTTP_STATUS_ERROR", message=f"Control Plane API returned HTTP {e.response.status_code}: {e.response.reason_phrase}", details={"status_code": e.response.status_code, "response_body": e.response.text[:500], "request_url": str(e.request.url), "params": params}))
        except httpx.TimeoutException as e:
            logger.error(f"❌ Control Plane API 查詢審計日誌請求超時: {e}", exc_info=True)
            return ToolResult(success=False, error=ToolError(code="TIMEOUT_ERROR", message=f"Control Plane API request timed out after {self.timeout}s", details={"timeout_seconds": self.timeout, "request_url": str(e.request.url) if hasattr(e, 'request') else None, "params": params}))
        except httpx.ConnectError as e:
            logger.error(f"❌ Control Plane API 查詢審計日誌連線失敗: {e}", exc_info=True)
            return ToolResult(success=False, error=ToolError(code="CONNECTION_ERROR", message=f"Failed to connect to Control Plane: {str(e)}", details={"base_url": self.base_url, "params": params}))
        except Exception as e:
            logger.error(f"❌ Control Plane 工具查詢審計日誌時發生未預期錯誤: {e}", exc_info=True)
            return ToolResult(success=False, error=ToolError(code="UNEXPECTED_ERROR", message=f"Unexpected error in Control Plane tool while querying audit logs: {str(e)}", details={"error_type": type(e).__name__, "params": params}))

    # --- Roadmap Task 1.3: ControlPlaneTool Implementation ---

    async def query_resources(self, params: Optional[Dict] = None) -> ToolResult:
        """
        查詢資源狀態 (GET /api/v1/resources)
        """
        try:
            logger.info(f"🛂 (ControlPlaneTool) 正在查詢資源，參數: {params}")
            response_data = await self._make_request(method="GET", endpoint="/api/v1/resources", params=params)
            resource_list = ResourceList.model_validate(response_data)
            return ToolResult(success=True, data=resource_list.model_dump())
        except ValidationError as e:
            return self._handle_validation_error(e, params)
        except httpx.HTTPStatusError as e:
            return self._handle_api_error(e, params)
        except httpx.TimeoutException as e:
            return self._handle_timeout_error(e, params)
        except httpx.ConnectError as e:
            return self._handle_connect_error(e, params)
        except Exception as e:
            return self._handle_unexpected_error(e, params)

    async def get_resource_details(self, resource_id: str) -> ToolResult:
        """
        獲取資源詳情 (GET /api/v1/resources/{resourceId})
        """
        try:
            logger.info(f"🛂 (ControlPlaneTool) 正在獲取資源 {resource_id} 的詳情...")
            response_data = await self._make_request(method="GET", endpoint=f"/api/v1/resources/{resource_id}")
            resource = Resource.model_validate(response_data)
            return ToolResult(success=True, data=resource.model_dump())
        except ValidationError as e:
            return self._handle_validation_error(e, {"resource_id": resource_id})
        except httpx.HTTPStatusError as e:
            return self._handle_api_error(e, {"resource_id": resource_id})
        except httpx.TimeoutException as e:
            return self._handle_timeout_error(e, {"resource_id": resource_id})
        except httpx.ConnectError as e:
            return self._handle_connect_error(e, {"resource_id": resource_id})
        except Exception as e:
            return self._handle_unexpected_error(e, {"resource_id": resource_id})

    async def query_resource_groups(self, params: Optional[Dict] = None) -> ToolResult:
        """
        查詢資源群組 (GET /api/v1/resource-groups)
        """
        try:
            logger.info(f"🛂 (ControlPlaneTool) 正在查詢資源群組，參數: {params}")
            response_data = await self._make_request(method="GET", endpoint="/api/v1/resource-groups", params=params)
            group_list = ResourceGroupList.model_validate(response_data)
            return ToolResult(success=True, data=group_list.model_dump())
        except ValidationError as e:
            return self._handle_validation_error(e, params)
        except httpx.HTTPStatusError as e:
            return self._handle_api_error(e, params)
        except httpx.TimeoutException as e:
            return self._handle_timeout_error(e, params)
        except httpx.ConnectError as e:
            return self._handle_connect_error(e, params)
        except Exception as e:
            return self._handle_unexpected_error(e, params)

    async def query_audit_logs(self, params: Optional[Dict] = None) -> ToolResult:
        """查詢部署相關的審計日誌 (GET /api/v1/audit-logs)"""
        try:
            logger.info(f"🛂 (ControlPlaneTool) 正在查詢審計日誌...")
            response = await self._make_request(method="GET", endpoint="/api/v1/audit-logs", params=params)
            return ToolResult(success=True, data={"logs": response.get("data", [])})
        except httpx.HTTPStatusError as e:
            return self._handle_api_error(e, params)
        except httpx.TimeoutException as e:
            return self._handle_timeout_error(e, params)
        except httpx.ConnectError as e:
            return self._handle_connect_error(e, params)
        except Exception as e:
            return self._handle_unexpected_error(e, params)

    async def query_incidents(self, params: Optional[Dict] = None) -> ToolResult:
        """查詢相關事件 (GET /api/v1/incidents)"""
        try:
            logger.info("🛂 (ControlPlaneTool) 正在查詢事件...")
            response = await self._make_request(method="GET", endpoint="/api/v1/incidents", params=params)
            return ToolResult(success=True, data={"incidents": response.get("data", [])})
        except httpx.HTTPStatusError as e:
            return self._handle_api_error(e, params)
        except httpx.TimeoutException as e:
            return self._handle_timeout_error(e, params)
        except httpx.ConnectError as e:
            return self._handle_connect_error(e, params)
        except Exception as e:
            return self._handle_unexpected_error(e, params)

    async def get_alert_rules(self, params: Optional[Dict] = None) -> ToolResult:
        """
        獲取告警規則狀態 (GET /api/v1/alert-rules)
        """
        try:
            logger.info(f"🛂 (ControlPlaneTool) 正在查詢告警規則，參數: {params}")
            response_data = await self._make_request(method="GET", endpoint="/api/v1/alert-rules", params=params)
            rule_list = AlertRuleList.model_validate(response_data)
            return ToolResult(success=True, data=rule_list.model_dump())
        except ValidationError as e:
            return self._handle_validation_error(e, params)
        except httpx.HTTPStatusError as e:
            return self._handle_api_error(e, params)
        except httpx.TimeoutException as e:
            return self._handle_timeout_error(e, params)
        except httpx.ConnectError as e:
            return self._handle_connect_error(e, params)
        except Exception as e:
            return self._handle_unexpected_error(e, params)

    async def query_automation_executions(self, params: Optional[Dict] = None) -> ToolResult:
        """
        查詢自動化腳本執行歷史 (GET /api/v1/automation/executions)
        """
        try:
            logger.info(f"🛂 (ControlPlaneTool) 正在查詢自動化腳本執行歷史，參數: {params}")
            response_data = await self._make_request(method="GET", endpoint="/api/v1/automation/executions", params=params)
            execution_list = ExecutionList.model_validate(response_data)
            return ToolResult(success=True, data=execution_list.model_dump())
        except ValidationError as e:
            return self._handle_validation_error(e, params)
        except httpx.HTTPStatusError as e:
            return self._handle_api_error(e, params)
        except httpx.TimeoutException as e:
            return self._handle_timeout_error(e, params)
        except httpx.ConnectError as e:
            return self._handle_connect_error(e, params)
        except Exception as e:
            return self._handle_unexpected_error(e, params)

    # --- Private Helper Methods for Error Handling ---

    def _handle_api_error(self, e: httpx.HTTPStatusError, params: Optional[Dict]) -> ToolResult:
        logger.error(f"❌ Control Plane API 失敗: {e.response.status_code} - {e.response.text}", exc_info=True)
        return ToolResult(success=False, error=ToolError(code="HTTP_STATUS_ERROR", message=f"Control Plane API returned HTTP {e.response.status_code}: {e.response.reason_phrase}", details={"status_code": e.response.status_code, "response_body": e.response.text[:500], "request_url": str(e.request.url), "params": params}))

    def _handle_timeout_error(self, e: httpx.TimeoutException, params: Optional[Dict]) -> ToolResult:
        logger.error(f"❌ Control Plane API 請求超時: {e}", exc_info=True)
        return ToolResult(success=False, error=ToolError(code="TIMEOUT_ERROR", message=f"Control Plane API request timed out after {self.timeout}s", details={"timeout_seconds": self.timeout, "request_url": str(e.request.url) if hasattr(e, 'request') else None, "params": params}))

    def _handle_connect_error(self, e: httpx.ConnectError, params: Optional[Dict]) -> ToolResult:
        logger.error(f"❌ Control Plane API 連線失敗: {e}", exc_info=True)
        return ToolResult(success=False, error=ToolError(code="CONNECTION_ERROR", message=f"Failed to connect to Control Plane: {str(e)}", details={"base_url": self.base_url, "params": params}))

    def _handle_validation_error(self, e: ValidationError, params: Optional[Dict]) -> ToolResult:
        logger.error(f"❌ Control Plane API 回應資料格式無效: {e}", exc_info=True)
        return ToolResult(success=False, error=ToolError(code="VALIDATION_ERROR", message="Control Plane API response data format invalid", details={"validation_errors": e.errors(), "params": params}))

    def _handle_unexpected_error(self, e: Exception, params: Optional[Dict]) -> ToolResult:
        logger.error(f"❌ Control Plane 工具執行時發生未預期錯誤: {e}", exc_info=True)
        return ToolResult(success=False, error=ToolError(code="UNEXPECTED_ERROR", message=f"Unexpected error in Control Plane tool: {str(e)}", details={"error_type": type(e).__name__, "params": params}))

    async def _get_auth_token(self) -> Optional[str]:
        """
        獲取或刷新 M2M 認證 Token
        
        實現了客戶端憑證流程和 Token 快取機制。
        """
        # 如果 Token 存在且尚未過期 (保留 60 秒的緩衝)，直接返回
        if self.token and self.token_expires_at > (time.time() + 60):
            return self.token

        logger.info("🔑 Token 過期或不存在，正在從 Keycloak 獲取新 Token...")
        
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                data = {
                    "client_id": self.client_id,
                    "client_secret": self.client_secret,
                    "grant_type": "client_credentials"
                }
                
                response = await client.post(self.token_url, data=data)
                
                if response.status_code != 200:
                    logger.error(f"❌ 從 Keycloak 獲取 Token 失敗: {response.status_code} - {response.text}")
                    return None
                
                token_data = response.json()
                self.token = token_data["access_token"]
                
                # 解碼 Token 以獲取過期時間
                decoded_token = jwt.decode(self.token, options={"verify_signature": False})
                self.token_expires_at = decoded_token.get("exp", 0)
                
                logger.info("✅ 成功獲取並快取了新的 Token")
                return self.token
                
        except Exception as e:
            logger.error(f"❌ 獲取 Token 時發生嚴重錯誤: {e}")
            return None

    async def _make_request(
        self,
        method: str,
        endpoint: str,
        params: Optional[Dict] = None,
        json_data: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """
        向 Control Plane API 發送認證請求
        """
        token = await self._get_auth_token()
        if not token:
            raise Exception("無法獲取認證 Token")
            
        headers = {
            "Authorization": f"Bearer {token}"
        }
        
        url = f"{self.base_url}{endpoint}"
        
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.request(
                method,
                url,
                headers=headers,
                params=params,
                json=json_data
            )
            
            if response.status_code >= 400:
                logger.error(f"❌ Control Plane API 請求失敗: {response.status_code} - {response.text}")
                response.raise_for_status() # 拋出 HTTP 錯誤
            
            return response.json()