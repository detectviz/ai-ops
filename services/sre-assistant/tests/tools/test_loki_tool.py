import pytest
import respx
import httpx
from httpx import Response
from unittest.mock import MagicMock

from sre_assistant.tools.loki_tool import LokiLogQueryTool

BASE_URL = "http://mock-loki"

@pytest.fixture
def mock_config():
    """提供一個模擬的 Loki 設定物件"""
    config = MagicMock()
    config.loki.base_url = BASE_URL
    config.loki.timeout_seconds = 5
    config.loki.default_limit = 100
    config.loki.max_time_range = 1440
    return config

@pytest.fixture
def http_client():
    """提供一個標準的 HTTP 客戶端供測試使用"""
    return httpx.AsyncClient()

@pytest.fixture
def loki_tool(mock_config, http_client):
    """初始化 LokiLogQueryTool 並注入 HTTP 客戶端"""
    return LokiLogQueryTool(mock_config, http_client)

@pytest.mark.asyncio
@respx.mock
async def test_loki_query_success(loki_tool: LokiLogQueryTool):
    """測試成功的日誌查詢與基本分析"""
    params = {"service": "test-app", "log_level": "error"}
    api_url = f"{BASE_URL}/loki/api/v1/query_range"
    
    mock_response_data = {
        "status": "success",
        "data": {
            "resultType": "streams",
            "result": [{"stream": {"app": "test-app"}, "values": [["1609459200000000000", "level=error msg=\"ComponentA: Connection refused\""], ["1609459100000000000", "level=error msg=\"ComponentB: OOMKilled event detected\""]]}]
        }
    }
    respx.get(url__regex=f"{api_url}.*").mock(return_value=Response(200, json=mock_response_data))
    
    result = await loki_tool.execute(params)
    
    assert result.success is True
    assert len(result.data["logs"]) == 2
    analysis = result.data["analysis"]
    assert analysis["total_logs"] == 2
    assert analysis["level_distribution"]["ERROR"] == 2

@pytest.mark.asyncio
@respx.mock
async def test_loki_api_error(loki_tool: LokiLogQueryTool):
    """測試當 Loki API 回傳 503 錯誤時，工具能正確處理"""
    params = {"service": "failing-service"}
    api_url = f"{BASE_URL}/loki/api/v1/query_range"
    respx.get(url__regex=f"{api_url}.*").mock(return_value=Response(503, text="Service Unavailable"))
    
    result = await loki_tool.execute(params)
    
    assert result.success is False
    assert result.error.code == "HTTP_STATUS_ERROR"
    assert "503" in result.error.message

@pytest.mark.asyncio
@respx.mock
async def test_loki_timeout_error(loki_tool: LokiLogQueryTool):
    """測試當 Loki API 請求超時，工具能正確處理"""
    params = {"service": "timeout-service"}
    api_url = f"{BASE_URL}/loki/api/v1/query_range"
    respx.get(url__regex=f"{api_url}.*").mock(side_effect=httpx.TimeoutException("Timeout occurred"))
    result = await loki_tool.execute(params)
    assert result.success is False
    assert result.error.code == "TIMEOUT_ERROR"

@pytest.mark.asyncio
@respx.mock
async def test_loki_connection_error(loki_tool: LokiLogQueryTool):
    """測試當 Loki API 連線失敗，工具能正確處理"""
    params = {"service": "connect-error-service"}
    api_url = f"{BASE_URL}/loki/api/v1/query_range"
    respx.get(url__regex=f"{api_url}.*").mock(side_effect=httpx.ConnectError("Connection failed"))
    result = await loki_tool.execute(params)
    assert result.success is False
    assert result.error.code == "CONNECTION_ERROR"

@pytest.mark.asyncio
@respx.mock
async def test_loki_query_with_filter(loki_tool: LokiLogQueryTool):
    """測試日誌過濾查詢是否能正確建構 LogQL"""
    params = {"service": "filtered-app", "namespace": "prod", "pattern": "traceID=xyz"}
    api_url = f"{BASE_URL}/loki/api/v1/query_range"
    route = respx.get(url__regex=f"{api_url}.*").mock(return_value=Response(200, json={"status": "success", "data": {"resultType": "streams", "result": []}}))
    await loki_tool.execute(params)
    assert route.call_count == 1
    query_param = route.calls[0].request.url.params["query"]
    assert 'app="filtered-app"' in query_param
    assert 'namespace="prod"' in query_param
    assert '|~ "traceID=xyz"' in query_param

@pytest.mark.asyncio
async def test_log_aggregation_logic(loki_tool: LokiLogQueryTool):
    """測試客戶端日誌聚合邏輯的正確性"""
    mock_logs = [
        {"message": "level=error msg=\"OOMKilled\"", "parsed": {"level": "ERROR", "error_type": "記憶體不足"}},
        {"message": "level=error msg=\"DB connection timeout\"", "parsed": {"level": "ERROR", "error_type": "連接超時"}},
        {"message": "level=warn msg=\"Slow query detected\"", "parsed": {"level": "WARN", "error_type": None}},
    ]
    analysis = loki_tool._analyze_logs(mock_logs)
    assert analysis["total_logs"] == 3
    assert analysis["level_distribution"] == {"ERROR": 2, "WARN": 1}
    assert analysis["error_types"] == {"記憶體不足": 1, "連接超時": 1}
