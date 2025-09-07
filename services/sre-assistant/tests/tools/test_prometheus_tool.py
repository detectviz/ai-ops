import pytest
import respx
import httpx
from httpx import Response
from unittest.mock import MagicMock, AsyncMock
import json

from sre_assistant.tools.prometheus_tool import PrometheusQueryTool
from sre_assistant.contracts import ToolResult

BASE_URL = "http://mock-prometheus"

@pytest.fixture
def mock_config():
    """提供一個模擬的 Prometheus 設定物件"""
    config = MagicMock()
    config.prometheus.base_url = BASE_URL
    config.prometheus.timeout_seconds = 5
    config.prometheus.default_step = "1m"
    config.prometheus.max_points = 11000
    # 修正: 確保 get 方法回傳一個確切的數值，而不是另一個 mock
    config.prometheus.get.return_value = 300
    return config

@pytest.fixture
def mock_redis_client():
    """建立一個模擬的 Redis 客戶端，並提供一個可操作的後端儲存"""
    redis_store = {}
    
    async def get(key):
        return redis_store.get(key)
    
    async def set(key, value, ex=None):
        redis_store[key] = value
        return True
        
    client = AsyncMock()
    client.get.side_effect = get
    client.set.side_effect = set
    
    return client, redis_store

@pytest.fixture
def prometheus_tool(mock_config, mock_redis_client):
    """初始化 PrometheusQueryTool 並注入模擬的 Redis 客戶端"""
    redis_client, _ = mock_redis_client
    tool = PrometheusQueryTool(mock_config, redis_client)
    return tool

@pytest.mark.asyncio
@respx.mock
async def test_prometheus_query_caching(prometheus_tool: PrometheusQueryTool, mock_redis_client):
    """測試成功的查詢會被快取，且第二次呼叫會命中快取"""
    redis_client, redis_store = mock_redis_client
    
    query = 'sum(rate(http_requests_total{service="test-service", namespace="default"}[5m]))'
    api_url = f"{BASE_URL}/api/v1/query"
    
    mock_response_data = {
        "status": "success",
        "data": { "resultType": "vector", "result": [{"metric": {}, "value": [1609459200, "12.34"]}] }
    }
    
    route = respx.get(url__regex=f"{api_url}.*").mock(return_value=Response(200, json=mock_response_data))
    
    result1 = await prometheus_tool._execute_instant_query(query)
    
    assert route.call_count == 1
    assert result1 == 12.34
    assert f"prometheus:instant:{query}" in redis_store
    
    result2 = await prometheus_tool._execute_instant_query(query)
    
    assert route.call_count == 1
    assert result2 == 12.34

@pytest.mark.asyncio
@respx.mock
async def test_prometheus_api_error(prometheus_tool: PrometheusQueryTool):
    """測試當 Prometheus API 回傳 500 錯誤時，工具能正確處理"""
    params = {"service": "failing-service", "metric_type": "traffic"}
    api_url = f"{BASE_URL}/api/v1/query"
    respx.get(url__regex=f"{api_url}.*").mock(return_value=Response(500, text="Internal Server Error"))
    
    result = await prometheus_tool.execute(params)
    
    assert isinstance(result, ToolResult)
    assert result.success is False
    assert result.error.code == "HTTP_STATUS_ERROR"
    assert "500" in result.error.message

@pytest.mark.asyncio
@respx.mock
async def test_prometheus_timeout_error(prometheus_tool: PrometheusQueryTool):
    """測試當 Prometheus API 請求超時，工具能正確處理"""
    params = {"service": "timeout-service", "metric_type": "traffic"}
    api_url = f"{BASE_URL}/api/v1/query"
    respx.get(url__regex=f"{api_url}.*").mock(side_effect=httpx.TimeoutException("Timeout occurred"))
    result = await prometheus_tool.execute(params)
    assert result.success is False
    assert result.error.code == "TIMEOUT_ERROR"

@pytest.mark.asyncio
@respx.mock
async def test_prometheus_connection_error(prometheus_tool: PrometheusQueryTool):
    """測試當 Prometheus API 連線失敗，工具能正確處理"""
    params = {"service": "connect-error-service", "metric_type": "traffic"}
    api_url = f"{BASE_URL}/api/v1/query"
    respx.get(url__regex=f"{api_url}.*").mock(side_effect=httpx.ConnectError("Connection failed"))
    result = await prometheus_tool.execute(params)
    assert result.success is False
    assert result.error.code == "CONNECTION_ERROR"

@pytest.mark.asyncio
@respx.mock
async def test_prometheus_cache_failure(prometheus_tool: PrometheusQueryTool, mock_redis_client, mocker):
    """測試當 Redis 快取失敗時，工具能回退到直接呼叫 API"""
    redis_client, _ = mock_redis_client
    mocker.patch.object(redis_client, 'get', side_effect=Exception("Redis GET failed"))
    mocker.patch.object(redis_client, 'set', side_effect=Exception("Redis SET failed"))
    query = 'sum(rate(http_requests_total{service="cache-fail-service"}[5m]))'
    api_url = f"{BASE_URL}/api/v1/query"
    mock_response_data = {"status": "success", "data": {"resultType": "vector", "result": [{"metric": {}, "value": [1609459200, "56.78"]}]}}
    route = respx.get(url__regex=f"{api_url}.*").mock(return_value=Response(200, json=mock_response_data))
    result = await prometheus_tool._execute_instant_query(query)
    assert route.call_count == 1
    assert result == 56.78

@pytest.mark.asyncio
@respx.mock
async def test_prometheus_cache_hit(prometheus_tool: PrometheusQueryTool, mock_redis_client):
    """測試當快取命中時，不會觸發 API 呼叫"""
    redis_client, redis_store = mock_redis_client
    query = 'sum(rate(http_requests_total{service="cache-hit-service"}[5m]))'
    api_url = f"{BASE_URL}/api/v1/query"
    cache_key = f"prometheus:instant:{query}"
    cached_value = 99.99
    redis_store[cache_key] = json.dumps(cached_value)
    route = respx.get(url__regex=f"{api_url}.*").mock(return_value=Response(200, json={"status": "success", "data": {"result": []}}))
    result = await prometheus_tool._execute_instant_query(query)
    assert route.call_count == 0
    assert result == cached_value

@pytest.mark.asyncio
@respx.mock
async def test_prometheus_cache_miss(prometheus_tool: PrometheusQueryTool, mock_redis_client, mocker):
    """測試當快取未命中時，會觸發 API 呼叫並將結果寫入快取"""
    redis_client, _ = mock_redis_client
    query = 'sum(rate(http_requests_total{service="cache-miss-service"}[5m]))'
    api_url = f"{BASE_URL}/api/v1/query"
    api_response_value = 45.67
    mock_response_data = {"status": "success", "data": { "resultType": "vector", "result": [{"metric": {}, "value": [1609459200, str(api_response_value)]}] }}
    route = respx.get(url__regex=f"{api_url}.*").mock(return_value=Response(200, json=mock_response_data))
    mocker.patch.object(redis_client, 'get', return_value=None)
    set_spy = mocker.spy(redis_client, 'set')
    result = await prometheus_tool._execute_instant_query(query)
    assert route.call_count == 1
    assert result == api_response_value
    cache_key = f"prometheus:instant:{query}"
    set_spy.assert_called_once_with(cache_key, json.dumps(api_response_value), ex=300)
