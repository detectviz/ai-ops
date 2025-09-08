# services/sre-assistant/tests/tools/test_control_plane_tool.py
"""
ControlPlaneTool 的單元測試
"""

import pytest
import respx
from httpx import Response, TimeoutException, ConnectError
from unittest.mock import MagicMock
from datetime import datetime, timezone

from sre_assistant.tools.control_plane_tool import ControlPlaneTool

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
def control_plane_tool(mock_config, mocker):
    """初始化 ControlPlaneTool 並模擬其認證流程"""
    mocker.patch(
        'sre_assistant.tools.control_plane_tool.ControlPlaneTool._get_auth_token',
        return_value="dummy-jwt-token"
    )
    tool = ControlPlaneTool(mock_config)
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
    mock_response = {"data": [{"id": "log2", "message": "Deployment updated"}]}
    respx.get(f"{BASE_URL}/api/v1/audit-logs").mock(return_value=Response(200, json=mock_response))
    result = await control_plane_tool.query_audit_logs()
    assert result.success is True
    assert len(result.data["logs"]) == 1

@pytest.mark.asyncio
@respx.mock
async def test_query_audit_logs_http_error(control_plane_tool: ControlPlaneTool):
    respx.get(f"{BASE_URL}/api/v1/audit-logs").mock(return_value=Response(503))
    result = await control_plane_tool.query_audit_logs()
    assert result.success is False
    assert result.error.code == "HTTP_STATUS_ERROR"


# --- 測試 get_resource_details ---

@pytest.mark.asyncio
@respx.mock
async def test_get_resource_details_success(control_plane_tool: ControlPlaneTool):
    mock_response = {"id": "res1", "name": "R1", "status": "healthy", "type": "db", "createdAt": NOW_ISO, "updatedAt": NOW_ISO}
    respx.get(f"{BASE_URL}/api/v1/resources/res1").mock(return_value=Response(200, json=mock_response))
    result = await control_plane_tool.get_resource_details("res1")
    assert result.success is True
    assert result.data["id"] == "res1"

@pytest.mark.asyncio
@respx.mock
async def test_get_resource_details_http_error(control_plane_tool: ControlPlaneTool):
    respx.get(f"{BASE_URL}/api/v1/resources/res1").mock(return_value=Response(404))
    result = await control_plane_tool.get_resource_details("res1")
    assert result.success is False
    assert result.error.code == "HTTP_STATUS_ERROR"

@pytest.mark.asyncio
@respx.mock
async def test_get_resource_details_validation_error(control_plane_tool: ControlPlaneTool):
    respx.get(f"{BASE_URL}/api/v1/resources/res1").mock(return_value=Response(200, json={"id": "res1"})) # Missing required fields
    result = await control_plane_tool.get_resource_details("res1")
    assert result.success is False
    assert result.error.code == "VALIDATION_ERROR"

# --- 測試 query_resource_groups ---

@pytest.mark.asyncio
@respx.mock
async def test_query_resource_groups_success(control_plane_tool: ControlPlaneTool):
    mock_response = {"items": [{"id": "grp1", "name": "G1", "resourceCount": 1, "createdAt": NOW_ISO, "updatedAt": NOW_ISO}], "total": 1}
    respx.get(f"{BASE_URL}/api/v1/resource-groups").mock(return_value=Response(200, json=mock_response))
    result = await control_plane_tool.query_resource_groups()
    assert result.success is True
    assert result.data["items"][0]["name"] == "G1"

# --- 測試 query_incidents ---

@pytest.mark.asyncio
@respx.mock
async def test_query_incidents_success(control_plane_tool: ControlPlaneTool):
    mock_response = {"data": [{"id": "inc1", "title": "Incident 1"}]}
    respx.get(f"{BASE_URL}/api/v1/incidents").mock(return_value=Response(200, json=mock_response))
    result = await control_plane_tool.query_incidents()
    assert result.success is True
    assert len(result.data["incidents"]) == 1

# --- 測試 get_alert_rules ---

@pytest.mark.asyncio
@respx.mock
async def test_get_alert_rules_success(control_plane_tool: ControlPlaneTool):
    mock_response = {"items": [{"id": "rule1", "name": "High CPU", "condition": {"metric": "cpu", "operator": ">", "threshold": 90, "duration": 300}, "severity": "critical", "enabled": True, "createdAt": NOW_ISO, "updatedAt": NOW_ISO}], "total": 1}
    respx.get(f"{BASE_URL}/api/v1/alert-rules").mock(return_value=Response(200, json=mock_response))
    result = await control_plane_tool.get_alert_rules()
    assert result.success is True
    assert result.data["items"][0]["name"] == "High CPU"

# --- 測試 query_automation_executions ---

@pytest.mark.asyncio
@respx.mock
async def test_query_automation_executions_success(control_plane_tool: ControlPlaneTool):
    mock_response = {"items": [{"id": "exec1", "scriptId": "s1", "scriptName": "reboot-pod", "status": "completed", "startedAt": NOW_ISO}], "pagination": {"page": 1, "pageSize": 10, "total": 1, "totalPages": 1}}
    respx.get(f"{BASE_URL}/api/v1/automation/executions").mock(return_value=Response(200, json=mock_response))
    result = await control_plane_tool.query_automation_executions()
    assert result.success is True
    assert result.data["items"][0]["script_name"] == "reboot-pod"

# --- 測試 check_health ---

@pytest.mark.asyncio
@respx.mock
async def test_check_health_success(control_plane_tool: ControlPlaneTool):
    respx.get(f"{BASE_URL}/api/v1/healthz").mock(return_value=Response(200, json={"status": "healthy"}))
    result = await control_plane_tool.check_health()
    assert result is True

@pytest.mark.asyncio
@respx.mock
async def test_check_health_failure(control_plane_tool: ControlPlaneTool):
    respx.get(f"{BASE_URL}/api/v1/healthz").mock(return_value=Response(500))
    result = await control_plane_tool.check_health()
    assert result is False

@pytest.mark.asyncio
@respx.mock
async def test_check_health_unhealthy_status(control_plane_tool: ControlPlaneTool):
    respx.get(f"{BASE_URL}/api/v1/healthz").mock(return_value=Response(200, json={"status": "unhealthy"}))
    result = await control_plane_tool.check_health()
    assert result is False


import time
from jose import jwt

class TestControlPlaneAuth:
    """專門測試 ControlPlaneTool 的認證流程"""

    @pytest.mark.asyncio
    @respx.mock
    async def test_get_token_success_and_cache(self, mock_config):
        """測試成功獲取 token，且第二次呼叫會使用快取"""
        tool = ControlPlaneTool(mock_config) # 不使用 mock `_get_auth_token` 的 fixture
        token_url = mock_config.auth.keycloak.token_url

        # 建立一個假的 JWT token
        expiry = int(time.time()) + 3600
        fake_token = jwt.encode({"exp": expiry, "sub": "test-client"}, "secret", algorithm="HS256")
        mock_response = {"access_token": fake_token, "expires_in": 3600}

        route = respx.post(token_url).mock(return_value=Response(200, json=mock_response))

        # 第一次呼叫
        token1 = await tool._get_auth_token()
        assert token1 == fake_token
        assert route.call_count == 1

        # 第二次呼叫應該命中快取
        token2 = await tool._get_auth_token()
        assert token2 == fake_token
        assert route.call_count == 1

    @pytest.mark.asyncio
    @respx.mock
    async def test_get_token_failure(self, mock_config):
        """測試從 Keycloak 獲取 token 失敗"""
        tool = ControlPlaneTool(mock_config)
        token_url = mock_config.auth.keycloak.token_url
        respx.post(token_url).mock(return_value=Response(401, json={"error": "unauthorized"}))

        token = await tool._get_auth_token()

        assert token is None

    @pytest.mark.asyncio
    @respx.mock
    async def test_token_refresh_on_expiry(self, mock_config):
        """測試當 token 過期時會自動刷新"""
        tool = ControlPlaneTool(mock_config)
        token_url = mock_config.auth.keycloak.token_url

        # 第一次的 token
        expiry1 = int(time.time()) + 3600
        fake_token1 = jwt.encode({"exp": expiry1}, "secret", "HS256")

        # 第二次的 token
        expiry2 = int(time.time()) + 3600
        fake_token2 = jwt.encode({"exp": expiry2}, "secret", "HS256")

        # 設定 respx 路由以依序返回不同的 token
        route = respx.post(token_url).mock(side_effect=[
            Response(200, json={"access_token": fake_token1}),
            Response(200, json={"access_token": fake_token2}),
        ])

        # 第一次呼叫
        token1 = await tool._get_auth_token()
        assert token1 == fake_token1
        assert route.call_count == 1

        # 手動將 token 設為已過期
        tool.token_expires_at = int(time.time()) - 1

        # 第二次呼叫，應該觸發刷新
        token2 = await tool._get_auth_token()
        assert token2 == fake_token2
        assert route.call_count == 2
