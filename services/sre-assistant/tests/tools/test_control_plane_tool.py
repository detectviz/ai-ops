# services/sre-assistant/tests/tools/test_control_plane_tool.py
"""
ControlPlaneTool 的整合測試 (已修正以符合目前的資料契約)
"""

import pytest
import respx
from httpx import Response
from unittest.mock import MagicMock

from sre_assistant.tools.control_plane_tool import ControlPlaneTool
from sre_assistant.contracts import ToolResult, ToolError

# 測試用的基本 URL
BASE_URL = "http://mock-control-plane"

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

@pytest.mark.asyncio
@respx.mock
async def test_query_resources_success(control_plane_tool: ControlPlaneTool):
    """測試：成功查詢資源列表並通過 Pydantic 驗證"""
    # 安排
    from datetime import datetime, timezone
    now = datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z')
    mock_response_data = {
        "items": [{
            "id": "res1", "name": "Resource 1", "status": "healthy", "type": "database",
            "createdAt": now, "updatedAt": now
        }],
        "pagination": {"page": 1, "pageSize": 10, "total": 1, "totalPages": 1}
    }
    respx.get(f"{BASE_URL}/api/v1/resources").mock(return_value=Response(200, json=mock_response_data))

    # 執行
    result = await control_plane_tool.query_resources()

    # 斷言
    assert isinstance(result, ToolResult)
    assert result.success is True
    assert len(result.data["items"]) == 1
    assert result.data["items"][0]["name"] == "Resource 1"
    assert result.data["pagination"]["total"] == 1

@pytest.mark.asyncio
@respx.mock
async def test_query_resources_api_error(control_plane_tool: ControlPlaneTool):
    """測試：查詢資源列表時 API 回傳 500 錯誤"""
    # 安排
    respx.get(f"{BASE_URL}/api/v1/resources").mock(return_value=Response(500))

    # 執行
    result = await control_plane_tool.query_resources()

    # 斷言
    assert isinstance(result, ToolError)
    assert result.code == "API_ERROR"
    assert "500" in result.message

@pytest.mark.asyncio
@respx.mock
async def test_query_resources_validation_error(control_plane_tool: ControlPlaneTool):
    """測試：查詢資源列表時 API 回傳格式錯誤的資料"""
    # 安排
    # 缺少 'items' 欄位，將導致 Pydantic 驗證失敗
    mock_invalid_data = {
        "pagination": {"page": 1, "pageSize": 10, "total": 1, "totalPages": 1}
    }
    respx.get(f"{BASE_URL}/api/v1/resources").mock(return_value=Response(200, json=mock_invalid_data))

    # 執行
    result = await control_plane_tool.query_resources()

    # 斷言
    assert isinstance(result, ToolError)
    assert result.code == "INVALID_DATA_FORMAT"
    assert "不符預期" in result.message

@pytest.mark.asyncio
@respx.mock
async def test_get_resource_details_success(control_plane_tool: ControlPlaneTool):
    """測試：成功獲取單一資源的詳情"""
    # 安排
    resource_id = "res-abc-123"
    # 修正：提供完整的 Resource 物件以通過 Pydantic 驗證
    from datetime import datetime, timezone
    now = datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z')

    mock_response_data = {
        "id": resource_id,
        "name": "Detailed Resource",
        "status": "active",
        "type": "server",
        "createdAt": now,
        "updatedAt": now
    }
    respx.get(f"{BASE_URL}/api/v1/resources/{resource_id}").mock(return_value=Response(200, json=mock_response_data))

    # 執行
    result = await control_plane_tool.get_resource_details(resource_id)

    # 斷言
    assert isinstance(result, ToolResult)
    assert result.success is True
    # 驗證返回的資料（Pydantic 模型轉換為 dict 後）與模擬資料匹配
    assert result.data["id"] == mock_response_data["id"]
    assert result.data["name"] == mock_response_data["name"]

@pytest.mark.asyncio
@respx.mock
async def test_query_resource_groups_success(control_plane_tool: ControlPlaneTool):
    """測試：成功查詢資源群組列表"""
    # 安排
    from datetime import datetime, timezone
    now = datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z')
    mock_response_data = {
        "items": [{
            "id": "grp1", "name": "Group 1", "resourceCount": 5,
            "createdAt": now, "updatedAt": now
        }],
        "total": 1
    }
    respx.get(f"{BASE_URL}/api/v1/resource-groups").mock(return_value=Response(200, json=mock_response_data))

    # 執行
    result = await control_plane_tool.query_resource_groups()

    # 斷言
    assert isinstance(result, ToolResult)
    assert result.success is True
    assert len(result.data["items"]) == 1
    assert result.data["items"][0]["name"] == "Group 1"

@pytest.mark.asyncio
@respx.mock
async def test_query_resource_groups_api_error(control_plane_tool: ControlPlaneTool):
    """測試：查詢資源群組時 API 回傳 500 錯誤"""
    # 安排
    respx.get(f"{BASE_URL}/api/v1/resource-groups").mock(return_value=Response(500, text="Internal Server Error"))

    # 執行
    result = await control_plane_tool.query_resource_groups()

    # 斷言
    assert isinstance(result, ToolError)
    assert result.code == "API_ERROR"
    assert "500" in result.message
    assert "Internal Server Error" in result.message

@pytest.mark.asyncio
@respx.mock
async def test_query_resource_groups_validation_error(control_plane_tool: ControlPlaneTool):
    """測試：查詢資源群組時 API 回傳格式錯誤的資料"""
    # 安排
    mock_invalid_data = {"items": [{"id": "grp1"}]} # 缺少 name, resourceCount 等欄位
    respx.get(f"{BASE_URL}/api/v1/resource-groups").mock(return_value=Response(200, json=mock_invalid_data))

    # 執行
    result = await control_plane_tool.query_resource_groups()

    # 斷言
    assert isinstance(result, ToolError)
    assert result.code == "INVALID_DATA_FORMAT"

@pytest.mark.asyncio
async def test_auth_token_is_mocked(control_plane_tool: ControlPlaneTool, mocker):
    """測試：確認 _get_auth_token 方法確實被模擬了"""
    # 執行
    token = await control_plane_tool._get_auth_token()

    # 斷言
    assert token == "dummy-jwt-token"
    control_plane_tool._get_auth_token.assert_called_once()

@pytest.mark.asyncio
@respx.mock
async def test_query_incidents_with_params(control_plane_tool: ControlPlaneTool):
    """測試：查詢事件時能正確傳遞查詢參數"""
    # 安排
    params = {"status": "active", "limit": "10"}
    mock_response_data = {"data": [{"id": "inc-1", "title": "Incident 1"}]}
    incident_route = respx.get(f"{BASE_URL}/api/v1/incidents", params=params).mock(return_value=Response(200, json=mock_response_data))

    # 執行
    result = await control_plane_tool.query_incidents(params=params)

    # 斷言
    assert incident_route.called
    assert result.success is True
    assert result.data["incidents"] == mock_response_data["data"]


# --- 新增的 Alert Rules 測試 ---

@pytest.mark.asyncio
@respx.mock
async def test_get_alert_rules_success(control_plane_tool: ControlPlaneTool):
    """測試：成功查詢告警規則列表"""
    from datetime import datetime, timezone
    now = datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z')
    mock_response_data = {
        "items": [{
            "id": "rule-1", "name": "High CPU", "severity": "critical", "enabled": True,
            "condition": {"metric": "cpu", "operator": "gt", "threshold": 90, "duration": 300},
            "createdAt": now, "updatedAt": now
        }],
        "total": 1
    }
    respx.get(f"{BASE_URL}/api/v1/alert-rules").mock(return_value=Response(200, json=mock_response_data))
    result = await control_plane_tool.get_alert_rules()
    assert isinstance(result, ToolResult)
    assert result.success is True
    assert result.data["items"][0]["name"] == "High CPU"

@pytest.mark.asyncio
@respx.mock
async def test_get_alert_rules_api_error(control_plane_tool: ControlPlaneTool):
    """測試：查詢告警規則時 API 回傳錯誤"""
    respx.get(f"{BASE_URL}/api/v1/alert-rules").mock(return_value=Response(503))
    result = await control_plane_tool.get_alert_rules()
    assert isinstance(result, ToolError)
    assert result.code == "API_ERROR"

@pytest.mark.asyncio
@respx.mock
async def test_get_alert_rules_validation_error(control_plane_tool: ControlPlaneTool):
    """測試：查詢告警規則時 API 回傳格式錯誤的資料"""
    mock_invalid_data = {"items": [{"id": "rule-1"}]} # 缺少必要欄位
    respx.get(f"{BASE_URL}/api/v1/alert-rules").mock(return_value=Response(200, json=mock_invalid_data))
    result = await control_plane_tool.get_alert_rules()
    assert isinstance(result, ToolError)
    assert result.code == "INVALID_DATA_FORMAT"


# --- 新增的 Automation Executions 測試 ---

@pytest.mark.asyncio
@respx.mock
async def test_query_automation_executions_success(control_plane_tool: ControlPlaneTool):
    """測試：成功查詢自動化執行歷史"""
    from datetime import datetime, timezone
    now = datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z')
    mock_response_data = {
        "items": [{
            "id": "exec-1", "scriptId": "s-1", "scriptName": "cleanup_tmp", "status": "success",
            "startedAt": now, "completedAt": now
        }],
        "pagination": {"page": 1, "pageSize": 10, "total": 1, "totalPages": 1}
    }
    respx.get(f"{BASE_URL}/api/v1/automation/executions").mock(return_value=Response(200, json=mock_response_data))
    result = await control_plane_tool.query_automation_executions()
    assert isinstance(result, ToolResult)
    assert result.success is True
    # 修正：Pydantic model_dump() 預設使用欄位名 (snake_case) 而非 alias (camelCase)
    assert result.data["items"][0]["script_name"] == "cleanup_tmp"

@pytest.mark.asyncio
@respx.mock
async def test_query_automation_executions_api_error(control_plane_tool: ControlPlaneTool):
    """測試：查詢自動化執行歷史時 API 回傳錯誤"""
    respx.get(f"{BASE_URL}/api/v1/automation/executions").mock(return_value=Response(500))
    result = await control_plane_tool.query_automation_executions()
    assert isinstance(result, ToolError)
    assert result.code == "API_ERROR"

@pytest.mark.asyncio
@respx.mock
async def test_query_automation_executions_validation_error(control_plane_tool: ControlPlaneTool):
    """測試：查詢自動化執行歷史時 API 回傳格式錯誤的資料"""
    mock_invalid_data = {"pagination": {"page": 1, "pageSize": 10, "total": 1, "totalPages": 1}} # 缺少 items
    respx.get(f"{BASE_URL}/api/v1/automation/executions").mock(return_value=Response(200, json=mock_invalid_data))
    result = await control_plane_tool.query_automation_executions()
    assert isinstance(result, ToolError)
    assert result.code == "INVALID_DATA_FORMAT"
