"""
SRE 工作流程測試 (已重構以匹配目前的實作)
"""

import pytest
import asyncio
import uuid
from unittest.mock import Mock, AsyncMock, patch

from sre_assistant.workflow import SREWorkflow
from sre_assistant.contracts import (
    DiagnosticRequest,
    ToolResult,
    ToolError,
    Finding,
    DiagnosticStatus,
    DiagnosticResult,
)


@pytest.fixture
def mock_config():
    """建立一個模擬的配置物件"""
    config = Mock()
    config.workflow = {
        "parallel_diagnosis": True,
        "diagnosis_timeout_seconds": 60,
        "max_retries": 2,
        "retry_delay_seconds": 0.01  # 測試時使用較短的延遲
    }
    # 為工具提供模擬配置，確保巢狀物件也支援屬性存取
    config.prometheus = Mock(base_url="http://mock-prometheus")
    config.loki = Mock(base_url="http://mock-loki")
    config.control_plane = Mock(base_url="http://mock-control-plane")
    return config

@pytest.fixture
def mock_redis_client():
    """建立一個模擬的 Redis 客戶端"""
    client = AsyncMock()
    # 模擬 get 和 set 方法
    # 使用一個字典來模擬 Redis 的儲存
    redis_store = {}

    async def get(key):
        return redis_store.get(key)

    async def set(key, value, ex=None):
        redis_store[key] = value
        return True

    client.get.side_effect = get
    client.set.side_effect = set

    # 在每次測試前清空 store
    redis_store.clear()

    return client, redis_store

@pytest.fixture
def workflow(mock_config, mock_redis_client):
    """建立一個帶有模擬依賴的工作流程實例"""
    redis_client, _ = mock_redis_client
    return SREWorkflow(mock_config, redis_client)


@pytest.mark.asyncio
async def test_diagnose_deployment_success(workflow, mock_redis_client):
    """
    測試一個成功的部署診斷流程。
    驗證：
    - 所有工具都被正確呼叫。
    - 任務狀態在 Redis 中被正確更新 (processing -> completed)。
    - 最終的 DiagnosticResult 包含來自所有工具的綜合結果。
    """
    redis_client, redis_store = mock_redis_client
    session_id = uuid.uuid4()
    request = DiagnosticRequest(
        incident_id="test-001",
        severity="P2",
        affected_services=["test-service"]
    )
    
    # 初始狀態
    initial_status = DiagnosticStatus(session_id=session_id, status="processing", progress=10, current_step="start")
    redis_store[str(session_id)] = initial_status.model_dump_json()

    # Mock 工具的 execute 方法
    workflow.prometheus_tool.execute = AsyncMock(return_value=ToolResult(
        success=True, data={"cpu_usage": "95%"}
    ))
    workflow.loki_tool.execute = AsyncMock(return_value=ToolResult(
        success=True, data={"critical_errors": 10}
    ))
    workflow.control_plane_tool.execute = AsyncMock(return_value=ToolResult(
        success=True, data={"recent_changes": True}
    ))

    # 執行工作流程的主要方法
    await workflow.execute(session_id, request, "deployment")

    # 驗證最終狀態
    final_status_json = await redis_client.get(str(session_id))
    assert final_status_json is not None
    final_status = DiagnosticStatus.model_validate_json(final_status_json)
    
    assert final_status.status == "completed"
    assert final_status.progress == 100
    assert final_status.result is not None
    assert len(final_status.result.findings) > 0  # 應該有發現
    assert final_status.result.summary is not None
    assert final_status.result.execution_time is not None
    
    # 驗證工具是否被呼叫
    workflow.prometheus_tool.execute.assert_called_once()
    workflow.loki_tool.execute.assert_called_once()
    workflow.control_plane_tool.execute.assert_called_once()


@pytest.mark.asyncio
async def test_diagnose_deployment_with_tool_failure(workflow, mock_redis_client):
    """
    測試當一個工具執行失敗時的場景。
    驗證：
    - 即使有工具失敗，工作流程也能完成。
    - 失敗的工具被記錄在最終結果中。
    - 成功的工具結果仍然被處理。
    """
    redis_client, redis_store = mock_redis_client
    session_id = uuid.uuid4()
    request = DiagnosticRequest(
        incident_id="test-002",
        severity="P1",
        affected_services=["failing-service"]
    )
    initial_status = DiagnosticStatus(session_id=session_id, status="processing", progress=10, current_step="start")
    redis_store[str(session_id)] = initial_status.model_dump_json()

    # Mock 工具，其中 Loki 會失敗
    workflow.prometheus_tool.execute = AsyncMock(return_value=ToolResult(
        success=True, data={"cpu_usage": "95%"}  # 觸發告警的條件
    ))
    workflow.loki_tool.execute = AsyncMock(side_effect=Exception("Loki connection failed"))
    workflow.control_plane_tool.execute = AsyncMock(return_value=ToolResult(
        success=True, data={"recent_changes": False}
    ))

    await workflow.execute(session_id, request, "deployment")

    final_status = DiagnosticStatus.model_validate_json(await redis_client.get(str(session_id)))
    
    assert final_status.status == "completed" # 流程應該還是完成了
    assert final_status.result is not None
    
    # 檢查 Prometheus 的發現是否還在
    assert any("Prometheus" in f.source for f in final_status.result.findings)
    # 檢查使用的工具列表
    assert "PrometheusQueryTool" in final_status.result.tools_used
    assert "ControlPlaneTool" in final_status.result.tools_used
    assert "LokiLogQueryTool" not in final_status.result.tools_used # 失敗的工具不應該在 "used" 列表

@pytest.mark.asyncio
async def test_workflow_catastrophic_failure(workflow, mock_redis_client):
    """
    測試當工作流程本身發生未預期錯誤時的場景。
    驗證：
    - 任務狀態被更新為 'failed'。
    - 錯誤訊息被記錄下來。
    """
    redis_client, redis_store = mock_redis_client
    session_id = uuid.uuid4()
    request = DiagnosticRequest(
        incident_id="test-003",
        severity="P0",
        affected_services=["critical-service"]
    )
    initial_status = DiagnosticStatus(session_id=session_id, status="processing", progress=10, current_step="start")
    redis_store[str(session_id)] = initial_status.model_dump_json()

    # Mock 一個在流程中會引發異常的內部函式
    with patch.object(workflow, '_diagnose_deployment', new_callable=AsyncMock) as mock_diagnose:
        mock_diagnose.side_effect = ValueError("Something broke badly")

        await workflow.execute(session_id, request, "deployment")

    final_status = DiagnosticStatus.model_validate_json(await redis_client.get(str(session_id)))
    
    assert final_status.status == "failed"
    assert "Something broke badly" in final_status.error

@pytest.mark.asyncio
async def test_tool_retry_logic(workflow, mock_redis_client):
    """
    測試工具的重試邏輯。
    驗證：
    - 失敗的工具會被重試指定的次數。
    - 如果重試後成功，流程會繼續。
    """
    redis_client, redis_store = mock_redis_client
    session_id = uuid.uuid4()
    request = DiagnosticRequest(
        incident_id="test-004",
        severity="P2",
        affected_services=["flaky-service"]
    )
    initial_status = DiagnosticStatus(session_id=session_id, status="processing", progress=10, current_step="start")
    redis_store[str(session_id)] = initial_status.model_dump_json()

    # Mock Loki 工具，它會先失敗兩次，第三次成功
    loki_tool_mock = AsyncMock(
        side_effect=[
            Exception("Attempt 1 failed"),
            Exception("Attempt 2 failed"),
            ToolResult(success=True, data={"log_volume": "normal"})
        ]
    )
    workflow.loki_tool.execute = loki_tool_mock
    workflow.prometheus_tool.execute = AsyncMock(return_value=ToolResult(success=True, data={}))
    workflow.control_plane_tool.execute = AsyncMock(return_value=ToolResult(success=True, data={}))

    await workflow.execute(session_id, request, "deployment")

    # 驗證 Loki 工具被呼叫了三次 (1次原始 + 2次重試)
    assert loki_tool_mock.call_count == 3
    
    final_status = DiagnosticStatus.model_validate_json(await redis_client.get(str(session_id)))
    assert final_status.status == "completed"
    assert "LokiLogQueryTool" in final_status.result.tools_used
