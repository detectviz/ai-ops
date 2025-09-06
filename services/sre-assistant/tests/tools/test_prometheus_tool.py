import pytest
import respx
from httpx import Response
from unittest.mock import MagicMock, AsyncMock
import json

from sre_assistant.tools.prometheus_tool import PrometheusQueryTool
from sre_assistant.contracts import ToolResult, ToolError

BASE_URL = "http://mock-prometheus"

@pytest.fixture
def mock_config():
    """提供一個模擬的 Prometheus 設定物件"""
    config = MagicMock()
    config.prometheus.base_url = BASE_URL
    config.prometheus.timeout_seconds = 5
    config.prometheus.default_step = "1m"
    config.prometheus.max_points = 11000
    config.prometheus.cache_ttl_seconds = 300
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
    
    # 安排
    query = 'sum(rate(http_requests_total{service="test-service", namespace="default"}[5m]))'
    api_url = f"{BASE_URL}/api/v1/query"
    
    mock_response_data = {
        "status": "success",
        "data": {
            "resultType": "vector",
            "result": [{"metric": {}, "value": [1609459200, "12.34"]}]
        }
    }
    
    # 模擬 API 端點
    route = respx.get(url__regex=f"{api_url}.*").mock(return_value=Response(200, json=mock_response_data))
    
    # 執行第一次呼叫 (應該會觸發 API call)
    result1 = await prometheus_tool._execute_instant_query(query)
    
    # 斷言
    assert route.call_count == 1
    assert result1 == 12.34
    
    # 檢查快取是否已寫入
    cache_key = f"prometheus:instant:{query}"
    assert cache_key in redis_store
    
    # 執行第二次呼叫 (應該會命中快取)
    result2 = await prometheus_tool._execute_instant_query(query)
    
    # 斷言
    assert route.call_count == 1  # API 呼叫次數未增加
    assert result2 == 12.34

@pytest.mark.asyncio
@respx.mock
async def test_prometheus_api_error(prometheus_tool: PrometheusQueryTool):
    """測試當 Prometheus API 回傳 500 錯誤時，工具能正確處理"""
    # 安排
    params = {"service": "failing-service", "metric_type": "traffic"}
    api_url = f"{BASE_URL}/api/v1/query"
    respx.get(url__regex=f"{api_url}.*").mock(return_value=Response(500, text="Internal Server Error"))
    
    # 執行
    result = await prometheus_tool.execute(params)
    
    # 斷言
    assert isinstance(result, ToolResult)
    assert result.success is False
    assert result.error.code == "API_ERROR"
    assert "500" in result.error.message
    assert "Internal Server Error" in result.error.message
