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

from sre_assistant.tools.control_plane_tool import ControlPlaneTool
from sre_assistant.contracts import ToolResult, ToolError

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
