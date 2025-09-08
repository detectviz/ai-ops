# services/sre-assistant/tests/tools/test_control_plane_tool.py
"""
ControlPlaneTool 的單元測試
"""

import pytest
import respx
import httpx
from httpx import Response, TimeoutException, ConnectError
from unittest.mock import MagicMock
from datetime import datetime, timezone
import time
from jose import jwt

from sre_assistant.tools.control_plane_tool import ControlPlaneTool
from sre_assistant.contracts import ToolResult

# 測試用的基本 URL 和通用時間戳
BASE_URL = "http://mock-control-plane"
NOW_ISO = datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z')

@pytest.fixture
def mock_config():
    """提供一個模擬的設定物件"""
    config = MagicMock()
    config.control_plane.base_url = BASE_URL
    config.control_plane.timeout_seconds = 5
    config.control_plane.client_id = "test-client"
    config.control_plane.client_secret = "test-secret"
    config.auth.keycloak.token_url = f"{BASE_URL}/auth/token"
    return config

@pytest.fixture
def http_client():
    """提供一個標準的 HTTP 客戶端供測試使用"""
    return httpx.AsyncClient()

@pytest.fixture
def control_plane_tool(mock_config, http_client, mocker):
    """初始化 ControlPlaneTool 並注入 HTTP 客戶端，同時模擬其認證流程"""
    mocker.patch(
        'sre_assistant.tools.control_plane_tool.ControlPlaneTool._get_auth_token',
        return_value="dummy-jwt-token"
    )
    tool = ControlPlaneTool(mock_config, http_client)
    return tool

# --- 通用錯誤測試 ---
@pytest.mark.asyncio
@respx.mock
async def test_generic_timeout_error(control_plane_tool: ControlPlaneTool):
    """測試任一端點的超時錯誤"""
    respx.get(f"{BASE_URL}/api/v1/resources").mock(side_effect=TimeoutException("Timeout"))
    result = await control_plane_tool.query_resources()
    assert result.success is False
    assert result.error.code == "TIMEOUT_ERROR"

@pytest.mark.asyncio
@respx.mock
async def test_generic_connection_error(control_plane_tool: ControlPlaneTool):
    """測試任一端點的連線錯誤"""
    respx.get(f"{BASE_URL}/api/v1/resources").mock(side_effect=ConnectError("Connection failed"))
    result = await control_plane_tool.query_resources()
    assert result.success is False
    assert result.error.code == "CONNECTION_ERROR"

# --- 測試 query_resources ---

@pytest.mark.asyncio
@respx.mock
async def test_query_resources_success(control_plane_tool: ControlPlaneTool):
    mock_response = {"items": [{"id": "res1", "name": "R1", "status": "healthy", "type": "db", "createdAt": NOW_ISO, "updatedAt": NOW_ISO}], "pagination": {"page": 1, "pageSize": 10, "total": 1, "totalPages": 1}}
    respx.get(f"{BASE_URL}/api/v1/resources").mock(return_value=Response(200, json=mock_response))
    result = await control_plane_tool.query_resources()
    assert result.success is True
    assert result.data["items"][0]["name"] == "R1"

@pytest.mark.asyncio
@respx.mock
async def test_query_resources_http_error(control_plane_tool: ControlPlaneTool):
    respx.get(f"{BASE_URL}/api/v1/resources").mock(return_value=Response(500))
    result = await control_plane_tool.query_resources()
    assert result.success is False
    assert result.error.code == "HTTP_STATUS_ERROR"

@pytest.mark.asyncio
@respx.mock
async def test_query_resources_validation_error(control_plane_tool: ControlPlaneTool):
    respx.get(f"{BASE_URL}/api/v1/resources").mock(return_value=Response(200, json={"items": [{"id": "invalid"}]}))
    result = await control_plane_tool.query_resources()
    assert result.success is False
    assert result.error.code == "VALIDATION_ERROR"

# --- 測試 get_audit_logs (舊版) ---

@pytest.mark.asyncio
@respx.mock
async def test_get_audit_logs_success(control_plane_tool: ControlPlaneTool):
    mock_response = {"logs": [{"id": "log1", "message": "User logged in"}]}
    respx.get(f"{BASE_URL}/v1/audit-logs").mock(return_value=Response(200, json=mock_response))
    result = await control_plane_tool.get_audit_logs("test-service")
    assert result.success is True
    assert len(result.data["logs"]) == 1

@pytest.mark.asyncio
@respx.mock
async def test_get_audit_logs_http_error(control_plane_tool: ControlPlaneTool):
    respx.get(f"{BASE_URL}/v1/audit-logs").mock(return_value=Response(404))
    result = await control_plane_tool.get_audit_logs("test-service")
    assert result.success is False
    assert result.error.code == "HTTP_STATUS_ERROR"

# --- 測試 query_audit_logs (新版) ---

@pytest.mark.asyncio
@respx.mock
async def test_query_audit_logs_success(control_plane_tool: ControlPlaneTool):
    mock_response = {
        "items": [{
            "id": "log2",
            "userId": "user-123",
            "action": "update_deployment",
            "targetResourceId": "dep-abc",
            "targetResourceType": "deployment",
            "status": "success",
            "timestamp": NOW_ISO
        }],
        "pagination": {"page": 1, "pageSize": 10, "total": 1, "totalPages": 1}
    }
    respx.get(f"{BASE_URL}/api/v1/audit-logs").mock(return_value=Response(200, json=mock_response))
    result = await control_plane_tool.query_audit_logs()
    assert result.success is True
    assert len(result.data["items"]) == 1
    assert result.data["items"][0]["action"] == "update_deployment"

@pytest.mark.asyncio
@respx.mock
async def test_query_audit_logs_http_error(control_plane_tool: ControlPlaneTool):
    respx.get(f"{BASE_URL}/api/v1/audit-logs").mock(return_value=Response(503))
    result = await control_plane_tool.query_audit_logs()
    assert result.success is False
    assert result.error.code == "HTTP_STATUS_ERROR"

# --- 測試 query_incidents ---

@pytest.mark.asyncio
@respx.mock
async def test_query_incidents_success(control_plane_tool: ControlPlaneTool):
    mock_response = {
        "items": [{
            "id": "inc-1",
            "title": "Database is slow",
            "status": "acknowledged",
            "severity": "P2",
            "createdAt": NOW_ISO,
            "updatedAt": NOW_ISO
        }],
        "pagination": {"page": 1, "pageSize": 10, "total": 1, "totalPages": 1}
    }
    respx.get(f"{BASE_URL}/api/v1/incidents").mock(return_value=Response(200, json=mock_response))
    result = await control_plane_tool.query_incidents()
    assert result.success is True
    assert len(result.data["items"]) == 1
    assert result.data["items"][0]["title"] == "Database is slow"

@pytest.mark.asyncio
@respx.mock
async def test_query_incidents_validation_error(control_plane_tool: ControlPlaneTool):
    respx.get(f"{BASE_URL}/api/v1/incidents").mock(return_value=Response(200, json={"items": [{"id": "invalid"}]}))
    result = await control_plane_tool.query_incidents()
    assert result.success is False
    assert result.error.code == "VALIDATION_ERROR"

class TestControlPlaneAuth:
    """專門測試 ControlPlaneTool 的認證流程"""

    @pytest.mark.asyncio
    @respx.mock
    async def test_get_token_success_and_cache(self, mock_config, http_client):
        """測試成功獲取 token，且第二次呼叫會使用快取"""
        tool = ControlPlaneTool(mock_config, http_client)
        token_url = mock_config.auth.keycloak.token_url

        expiry = int(time.time()) + 3600
        fake_token = jwt.encode({"exp": expiry, "sub": "test-client"}, "secret", algorithm="HS256")
        mock_response = {"access_token": fake_token, "expires_in": 3600}

        route = respx.post(token_url).mock(return_value=Response(200, json=mock_response))

        token1 = await tool._get_auth_token()
        assert token1 == fake_token
        assert route.call_count == 1

        token2 = await tool._get_auth_token()
        assert token2 == fake_token
        assert route.call_count == 1

    @pytest.mark.asyncio
    @respx.mock
    async def test_get_token_failure(self, mock_config, http_client):
        """測試從 Keycloak 獲取 token 失敗"""
        tool = ControlPlaneTool(mock_config, http_client)
        token_url = mock_config.auth.keycloak.token_url
        respx.post(token_url).mock(return_value=Response(401, json={"error": "unauthorized"}))

        token = await tool._get_auth_token()

        assert token is None

    @pytest.mark.asyncio
    @respx.mock
    async def test_token_refresh_on_expiry(self, mock_config, http_client):
        """測試當 token 過期時會自動刷新"""
        tool = ControlPlaneTool(mock_config, http_client)
        token_url = mock_config.auth.keycloak.token_url

        expiry1 = int(time.time()) + 3600
        fake_token1 = jwt.encode({"exp": expiry1}, "secret", "HS256")

        expiry2 = int(time.time()) + 3600
        fake_token2 = jwt.encode({"exp": expiry2}, "secret", "HS256")

        route = respx.post(token_url).mock(side_effect=[
            Response(200, json={"access_token": fake_token1}),
            Response(200, json={"access_token": fake_token2}),
        ])

        token1 = await tool._get_auth_token()
        assert token1 == fake_token1
        assert route.call_count == 1

        tool.token_expires_at = int(time.time()) - 1

        token2 = await tool._get_auth_token()
        assert token2 == fake_token2
        assert route.call_count == 2

# --- 測試 acknowledge_incident ---

@pytest.mark.asyncio
@respx.mock
async def test_acknowledge_incident_success(control_plane_tool: ControlPlaneTool):
    """測試成功確認事件"""
    incident_id = "inc-123"
    mock_response = {
        "id": incident_id,
        "title": "Test Incident",
        "status": "acknowledged",
        "severity": "P1",
        "createdAt": NOW_ISO,
        "updatedAt": NOW_ISO
    }
    respx.post(f"{BASE_URL}/api/v1/incidents/{incident_id}/acknowledge").mock(return_value=Response(200, json=mock_response))

    result = await control_plane_tool.acknowledge_incident(incident_id, acknowledged_by="test-user")

    assert result.success is True
    assert result.data["id"] == incident_id
    assert result.data["status"] == "acknowledged"

@pytest.mark.asyncio
@respx.mock
async def test_acknowledge_incident_not_found(control_plane_tool: ControlPlaneTool):
    """測試確認一個不存在的事件"""
    incident_id = "inc-404"
    respx.post(f"{BASE_URL}/api/v1/incidents/{incident_id}/acknowledge").mock(return_value=Response(404))

    result = await control_plane_tool.acknowledge_incident(incident_id)

    assert result.success is False
    assert result.error.code == "HTTP_STATUS_ERROR"
    assert result.error.details["status_code"] == 404

# --- 測試 execute_script ---

@pytest.mark.asyncio
@respx.mock
async def test_execute_script_success(control_plane_tool: ControlPlaneTool):
    """測試成功執行腳本"""
    mock_response = {
        "executionId": "exec-abc",
        "status": "pending",
        "message": "Execution started"
    }
    respx.post(f"{BASE_URL}/api/v1/automation/execute").mock(return_value=Response(202, json=mock_response))

    result = await control_plane_tool.execute_script(script_id="script-1", target_resources=["res-1"])

    assert result.success is True
    assert result.data["execution_id"] == "exec-abc"
    assert result.data["status"] == "pending"

@pytest.mark.asyncio
@respx.mock
async def test_execute_script_bad_request(control_plane_tool: ControlPlaneTool):
    """測試執行腳本時參數錯誤"""
    respx.post(f"{BASE_URL}/api/v1/automation/execute").mock(return_value=Response(400, json={"error": "Invalid script ID"}))

    result = await control_plane_tool.execute_script(script_id="invalid-script")

    assert result.success is False
    assert result.error.code == "HTTP_STATUS_ERROR"
    assert result.error.details["status_code"] == 400

@pytest.mark.asyncio
@respx.mock
async def test_execute_script_validation_error(control_plane_tool: ControlPlaneTool):
    """測試執行腳本後的回應格式不正確"""
    # 回應缺少必要的 'executionId' 欄位
    mock_response = {"status": "pending"}
    respx.post(f"{BASE_URL}/api/v1/automation/execute").mock(return_value=Response(202, json=mock_response))

    result = await control_plane_tool.execute_script(script_id="script-1")

    assert result.success is False
    assert result.error.code == "VALIDATION_ERROR"
