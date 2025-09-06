# services/sre-assistant/src/sre_assistant/tools/control_plane_tool.py
"""
Control Plane 整合工具
用於回調 Control Plane API 獲取審計日誌和變更歷史
"""

import logging
import httpx
from typing import Dict, Any, Optional, List, Union
from datetime import datetime, timedelta, timezone
import jwt
import time

from ..contracts import ToolResult, ToolError

logger = logging.getLogger(__name__)


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

    async def get_audit_logs(self, service_name: str, limit: int = 10) -> List[Dict[str, Any]]:
        """
        查詢指定服務的審計日誌
        
        Args:
            service_name: 服務名稱
            limit: 返回的日誌數量
            
        Returns:
            審計日誌列表
        """
        logger.info(f"🛂 正在向 Control Plane 查詢 {service_name} 的審計日誌...")
        
        params = {
            "service_name": service_name,
            "limit": limit
        }
        
        response = await self._make_request(
            method="GET",
            endpoint="/v1/audit-logs",
            params=params
        )
        
        return response.get("logs", [])

    # --- Roadmap Task 1.3: ControlPlaneTool Implementation ---

    async def query_resources(self, params: Optional[Dict] = None) -> Union[ToolResult, ToolError]:
        """查詢資源狀態 (GET /api/v1/resources)"""
        try:
            logger.info("🛂 (ControlPlaneTool) 正在查詢資源...")
            response = await self._make_request(
                method="GET",
                endpoint="/api/v1/resources",
                params=params
            )
            # 修正：data 應為 dict
            return ToolResult(success=True, data={"resources": response.get("data", [])})
        except Exception as e:
            logger.error(f"❌ (ControlPlaneTool) 查詢資源時發生錯誤: {e}", exc_info=True)
            # 修正：使用正確的 ToolError 模型
            return ToolError(code="QUERY_FAILED", message=str(e), details={"source": "control_plane_tool"})

    async def get_resource_details(self, resource_id: str) -> Union[ToolResult, ToolError]:
        """獲取資源詳情 (GET /api/v1/resources/{resourceId})"""
        try:
            logger.info(f"🛂 (ControlPlaneTool) 正在獲取資源 {resource_id} 的詳情...")
            response = await self._make_request(
                method="GET",
                endpoint=f"/api/v1/resources/{resource_id}"
            )
            return ToolResult(success=True, data=response)
        except Exception as e:
            logger.error(f"❌ (ControlPlaneTool) 獲取資源詳情時發生錯誤: {e}", exc_info=True)
            return ToolError(code="GET_DETAILS_FAILED", message=str(e), details={"resource_id": resource_id})

    async def query_resource_groups(self, params: Optional[Dict] = None) -> Union[ToolResult, ToolError]:
        """查詢資源群組 (GET /api/v1/resource-groups)"""
        try:
            logger.info("🛂 (ControlPlaneTool) 正在查詢資源群組...")
            response = await self._make_request(
                method="GET",
                endpoint="/api/v1/resource-groups",
                params=params
            )
            return ToolResult(success=True, data={"groups": response.get("data", [])})
        except Exception as e:
            logger.error(f"❌ (ControlPlaneTool) 查詢資源群組時發生錯誤: {e}", exc_info=True)
            return ToolError(code="QUERY_FAILED", message=str(e), details={"source": "control_plane_tool"})

    async def query_audit_logs(self, params: Optional[Dict] = None) -> Union[ToolResult, ToolError]:
        """查詢部署相關的審計日誌 (GET /api/v1/audit-logs)"""
        try:
            logger.info("🛂 (ControlPlaneTool) 正在查詢審計日誌...")
            response = await self._make_request(
                method="GET",
                endpoint="/api/v1/audit-logs",
                params=params
            )
            return ToolResult(success=True, data={"logs": response.get("data", [])})
        except Exception as e:
            logger.error(f"❌ (ControlPlaneTool) 查詢審計日誌時發生錯誤: {e}", exc_info=True)
            return ToolError(code="QUERY_FAILED", message=str(e), details={"source": "control_plane_tool"})

    async def query_incidents(self, params: Optional[Dict] = None) -> Union[ToolResult, ToolError]:
        """查詢相關事件 (GET /api/v1/incidents)"""
        try:
            logger.info("🛂 (ControlPlaneTool) 正在查詢事件...")
            response = await self._make_request(
                method="GET",
                endpoint="/api/v1/incidents",
                params=params
            )
            return ToolResult(success=True, data={"incidents": response.get("data", [])})
        except Exception as e:
            logger.error(f"❌ (ControlPlaneTool) 查詢事件時發生錯誤: {e}", exc_info=True)
            return ToolError(code="QUERY_FAILED", message=str(e), details={"source": "control_plane_tool"})

    async def get_alert_rules(self, params: Optional[Dict] = None) -> Union[ToolResult, ToolError]:
        """獲取告警規則狀態 (GET /api/v1/alert-rules)"""
        try:
            logger.info("🛂 (ControlPlaneTool) 正在查詢告警規則...")
            response = await self._make_request(
                method="GET",
                endpoint="/api/v1/alert-rules",
                params=params
            )
            return ToolResult(success=True, data={"rules": response.get("data", [])})
        except Exception as e:
            logger.error(f"❌ (ControlPlaneTool) 查詢告警規則時發生錯誤: {e}", exc_info=True)
            return ToolError(code="QUERY_FAILED", message=str(e), details={"source": "control_plane_tool"})

    async def query_automation_executions(self, params: Optional[Dict] = None) -> Union[ToolResult, ToolError]:
        """查詢自動化腳本執行歷史 (GET /api/v1/automation/executions)"""
        try:
            logger.info("🛂 (ControlPlaneTool) 正在查詢自動化腳本執行歷史...")
            response = await self._make_request(
                method="GET",
                endpoint="/api/v1/automation/executions",
                params=params
            )
            return ToolResult(success=True, data={"executions": response.get("data", [])})
        except Exception as e:
            logger.error(f"❌ (ControlPlaneTool) 查詢自動化腳本執行歷史時發生錯誤: {e}", exc_info=True)
            return ToolError(code="QUERY_FAILED", message=str(e), details={"source": "control_plane_tool"})

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