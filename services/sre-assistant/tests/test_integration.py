import pytest
import os
from fastapi.testclient import TestClient
from unittest.mock import patch, AsyncMock
import uuid

# 確保在 app 匯入前設定環境變數
os.environ["ENVIRONMENT"] = "development" # 使用 development 設定以連接真實服務

from sre_assistant.main import app
from sre_assistant.tools.prometheus_tool import PrometheusQueryTool
from sre_assistant.tools.loki_tool import LokiLogQueryTool
from sre_assistant.tools.control_plane_tool import ControlPlaneTool
from sre_assistant.config.config_manager import ConfigManager

# 注意：這些是整合測試，它們會嘗試連接到在本地運行的真實服務。
# 在執行前，請確保已透過 `make start-services` 啟動所有依賴項。

@pytest.fixture(scope="module")
def client():
    """建立一個 TestClient 實例，用於整個模組的測試"""
    with TestClient(app) as c:
        yield c

@pytest.fixture(scope="module")
def config():
    """載入 development 環境的設定"""
    return ConfigManager(env="development").get_config()

@pytest.mark.integration
class TestKeycloakIntegration:
    """測試與真實 Keycloak 服務的整合"""

    @pytest.fixture(scope="class")
    def control_plane_tool(self, config):
        """為這個測試類別建立一個 ControlPlaneTool 實例"""
        return ControlPlaneTool(config)

    @pytest.mark.asyncio
    async def test_get_real_m2m_token(self, control_plane_tool: ControlPlaneTool):
        """測試是否能成功從 Keycloak 獲取 M2M token"""
        token = await control_plane_tool._get_auth_token()
        assert token is not None
        assert isinstance(token, str)
        assert len(token) > 50  # JWTs are typically long

    @pytest.mark.asyncio
    async def test_access_protected_endpoint_with_real_token(self, client, control_plane_tool: ControlPlaneTool):
        """測試使用真實 token 存取受保護的端點"""
        # 獲取真實 token
        token = await control_plane_tool._get_auth_token()
        assert token is not None

        headers = {"Authorization": f"Bearer {token}"}
        response = client.get("/api/v1/tools/status", headers=headers)
        
        assert response.status_code == 200
        data = response.json()
        assert "prometheus" in data
        assert data["prometheus"]["status"] == "healthy"

    def test_access_protected_endpoint_with_bad_token(self, client):
        """測試使用無效 token 存取時會被拒絕"""
        headers = {"Authorization": "Bearer a-very-bad-token"}
        response = client.get("/api/v1/tools/status", headers=headers)
        
        # 預期會收到 401 Unauthorized
        assert response.status_code == 401
        assert "Token" in response.json()["detail"]

@pytest.mark.integration
class TestToolIntegration:
    """測試工具與真實後端服務 (Prometheus, Loki) 的整合"""

    @pytest.fixture(scope="class")
    def prometheus_tool(self, config):
        """為這個測試類別建立一個 PrometheusQueryTool 實例"""
        # 整合測試不使用 Redis 快取，以確保每次都命中真實服務
        return PrometheusQueryTool(config, redis_client=None)

    @pytest.fixture(scope="class")
    def loki_tool(self, config):
        """為這個測試類別建立一個 LokiLogQueryTool 實例"""
        return LokiLogQueryTool(config)

    @pytest.mark.asyncio
    async def test_prometheus_query_integration(self, prometheus_tool: PrometheusQueryTool):
        """
        測試對本地 Prometheus (VictoriaMetrics) 執行一個簡單的查詢。
        斷言查詢成功，但不檢查具體數值，因為數值可能不穩定。
        """
        params = {"query": "up"}
        result = await prometheus_tool.execute(params)
        
        assert isinstance(result, ToolResult)
        assert result.success is True
        assert "value" in result.data
        # 'up' 查詢應該回傳 1
        assert result.data["value"] is not None

    @pytest.mark.asyncio
    async def test_loki_query_integration(self, loki_tool: LokiLogQueryTool):
        """
        測試對本地 Loki 執行一個簡單的查詢。
        斷言查詢成功，但不檢查具體的日誌內容。
        """
        params = {"service": "sre-assistant"} # 查詢自己的日誌
        result = await loki_tool.execute(params)
        
        assert isinstance(result, ToolResult)
        assert result.success is True
        assert "logs" in result.data
        assert "analysis" in result.data
