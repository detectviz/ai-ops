import pytest
import respx
from httpx import Response
from unittest.mock import MagicMock

from sre_assistant.tools.loki_tool import LokiLogQueryTool
from sre_assistant.contracts import ToolResult, ToolError

BASE_URL = "http://mock-loki"

@pytest.fixture
def mock_config():
    """提供一個模擬的 Loki 設定物件"""
    config = MagicMock()
    config.loki.base_url = BASE_URL
    config.loki.timeout_seconds = 5
    config.loki.default_limit = 100
    config.loki.max_time_range = 1440 # 24 hours in minutes
    return config

@pytest.fixture
def loki_tool(mock_config):
    """初始化 LokiLogQueryTool"""
    return LokiLogQueryTool(mock_config)

@pytest.mark.asyncio
@respx.mock
async def test_loki_query_success(loki_tool: LokiLogQueryTool):
    """測試成功的日誌查詢與基本分析"""
    # 安排
    params = {"service": "test-app", "log_level": "error"}
    api_url = f"{BASE_URL}/loki/api/v1/query_range"

    # 模擬一個包含錯誤日誌的回應
    mock_response_data = {
        "status": "success",
        "data": {
            "resultType": "streams",
            "result": [{
                "stream": {"app": "test-app"},
                "values": [
                    ["1609459200000000000", "level=error msg=\"ComponentA: Connection refused\""],
                    ["1609459100000000000", "level=error msg=\"ComponentB: OOMKilled event detected\""]
                ]
            }]
        }
    }
    respx.get(url__regex=f"{api_url}.*").mock(return_value=Response(200, json=mock_response_data))

    # 執行
    result = await loki_tool.execute(params)

    # 斷言
    assert isinstance(result, ToolResult)
    assert result.success is True
    assert len(result.data["logs"]) == 2
    assert "Connection refused" in result.data["logs"][0]["message"]

    # 驗證分析結果
    analysis = result.data["analysis"]
    assert analysis["total_logs"] == 2
    assert analysis["level_distribution"]["ERROR"] == 2
    assert analysis["error_types"]["連接被拒絕"] == 1
    assert "發現 1 次記憶體不足錯誤 (OOMKilled)" in analysis["critical_indicators"]

@pytest.mark.asyncio
@respx.mock
async def test_loki_api_error(loki_tool: LokiLogQueryTool):
    """測試當 Loki API 回傳 503 錯誤時，工具能正確處理"""
    # 安排
    params = {"service": "failing-service"}
    api_url = f"{BASE_URL}/loki/api/v1/query_range"
    respx.get(url__regex=f"{api_url}.*").mock(return_value=Response(503, text="Service Unavailable"))

    # 執行
    result = await loki_tool.execute(params)

    # 斷言
    assert isinstance(result, ToolResult)
    assert result.success is False
    assert result.error.code == "API_ERROR"
    assert "503" in result.error.message
    assert "Service Unavailable" in result.error.message

@pytest.mark.asyncio
@respx.mock
async def test_loki_query_with_filter(loki_tool: LokiLogQueryTool):
    """測試日誌過濾查詢是否能正確建構 LogQL"""
    # 安排
    params = {"service": "filtered-app", "namespace": "prod", "pattern": "traceID=xyz"}
    api_url = f"{BASE_URL}/loki/api/v1/query_range"

    # 模擬一個空回應即可，重點是驗證請求的 URL
    route = respx.get(url__regex=f"{api_url}.*").mock(return_value=Response(200, json={"status": "success", "data": {"resultType": "streams", "result": []}}))

    # 執行
    await loki_tool.execute(params)

    # 斷言
    assert route.call_count == 1
    request_url = route.calls[0].request.url
    query_param = request_url.params["query"]

    assert 'app="filtered-app"' in query_param
    assert 'namespace="prod"' in query_param
    assert '|~ "traceID=xyz"' in query_param

@pytest.mark.asyncio
async def test_log_aggregation_logic(loki_tool: LokiLogQueryTool):
    """測試客戶端日誌聚合邏輯的正確性"""
    # 安排
    mock_logs = [
        {"message": "level=error msg=\"OOMKilled\"", "parsed": {"level": "ERROR", "error_type": "記憶體不足"}},
        {"message": "level=error msg=\"DB connection timeout\"", "parsed": {"level": "ERROR", "error_type": "連接超時"}},
        {"message": "level=warn msg=\"Slow query detected\"", "parsed": {"level": "WARN", "error_type": None}},
        {"message": "level=info msg=\"User logged in\"", "parsed": {"level": "INFO", "error_type": None}},
        {"message": "level=error msg=\"OOMKilled again\"", "parsed": {"level": "ERROR", "error_type": "記憶體不足"}},
    ]

    # 執行
    analysis = loki_tool._analyze_logs(mock_logs)

    # 斷言
    assert analysis["total_logs"] == 5
    assert analysis["level_distribution"] == {"ERROR": 3, "WARN": 1, "INFO": 1}
    assert analysis["error_types"] == {"記憶體不足": 2, "連接超時": 1}
