"""
SRE 工作流程測試 (已重構以匹配目前的實作)
"""

import pytest
import uuid
import httpx
from unittest.mock import Mock, AsyncMock, patch

from sre_assistant.workflow import SREWorkflow
from sre_assistant.contracts import (
    DiagnosticRequest,
    ToolResult,
    ToolError,
    DiagnosticStatus,
    AlertAnalysisRequest,
    CapacityAnalysisRequest,
    ExecuteRequest,
)


@pytest.fixture
def mock_config():
    """建立一個模擬的配置物件"""
    config = Mock()
    config.workflow = {
        "parallel_diagnosis": True,
        "diagnosis_timeout_seconds": 60,
        "max_retries": 2,
        "retry_delay_seconds": 0.01
    }
    config.prometheus = Mock(base_url="http://mock-prometheus")
    config.loki = Mock(base_url="http://mock-loki")
    config.control_plane = Mock(base_url="http://mock-control-plane")
    return config

@pytest.fixture
def mock_redis_client():
    """建立一個模擬的 Redis 客戶端"""
    redis_store = {}

    async def get(key):
        return redis_store.get(key)

    async def set(key, value, ex=None):
        redis_store[key] = value
        return True

    client = AsyncMock()
    client.get.side_effect = get
    client.set.side_effect = set
    
    # 將 store 也返回，以便在測試中操作
    return client, redis_store

@pytest.fixture
def http_client():
    """提供一個標準的 HTTP 客戶端供測試使用"""
    return httpx.AsyncClient()

@pytest.fixture
def workflow(mock_config, mock_redis_client, http_client):
    """建立一個帶有模擬依賴的工作流程實例"""
    redis_client, _ = mock_redis_client
    return SREWorkflow(mock_config, redis_client, http_client)


@pytest.mark.asyncio
async def test_diagnose_deployment_success_e2e(workflow, mock_redis_client):
    """
    測試一個成功的部署診斷流程 (端到端)。
    """
    redis_client, redis_store = mock_redis_client
    session_id = uuid.uuid4()
    service_name = "test-service"
    request = DiagnosticRequest(
        incident_id="test-001",
        severity="P2",
        affected_services=[service_name]
    )
    
    initial_status = DiagnosticStatus(session_id=session_id, status="processing", progress=10, current_step="start")
    redis_store[str(session_id)] = initial_status.model_dump_json()

    workflow.prometheus_tool.execute = AsyncMock(return_value=ToolResult(
        success=True, data={"cpu_usage": "95%"}
    ))
    workflow.loki_tool.execute = AsyncMock(return_value=ToolResult(
        success=True, data={"analysis": {"critical_indicators": ["發現 5 次 OOMKilled"]}}
    ))
    workflow.control_plane_tool.query_audit_logs = AsyncMock(return_value=ToolResult(
        success=True, data={"logs": [{"user": "test-user", "action": "deploy"}]}
    ))
    workflow.control_plane_tool.query_incidents = AsyncMock(return_value=ToolResult(
        success=True, data={"incidents": [{"id": "INC-999", "title": "Related DB issue"}]}
    ))

    await workflow.execute(session_id, request, "deployment")

    final_status_json = await redis_client.get(str(session_id))
    assert final_status_json is not None
    final_status = DiagnosticStatus.model_validate_json(final_status_json)
    
    assert final_status.status == "completed"
    assert final_status.progress == 100
    assert final_status.result is not None
    
    workflow.prometheus_tool.execute.assert_called_once()
    workflow.loki_tool.execute.assert_called_once()
    workflow.control_plane_tool.query_audit_logs.assert_called_once()
    workflow.control_plane_tool.query_incidents.assert_called_once()
    
    findings = final_status.result.findings
    assert len(findings) == 4

@pytest.mark.asyncio
async def test_diagnose_deployment_with_tool_failure(workflow, mock_redis_client):
    """測試當一個工具執行失敗時的場景。"""
    redis_client, redis_store = mock_redis_client
    session_id = uuid.uuid4()
    request = DiagnosticRequest(incident_id="test-002", severity="P1", affected_services=["failing-service"])
    initial_status = DiagnosticStatus(session_id=session_id, status="processing", progress=10, current_step="start")
    redis_store[str(session_id)] = initial_status.model_dump_json()

    workflow.prometheus_tool.execute = AsyncMock(return_value=ToolResult(success=True, data={"cpu_usage": "95%"}))
    workflow.loki_tool.execute = AsyncMock(side_effect=Exception("Loki connection failed"))
    workflow.control_plane_tool.query_audit_logs = AsyncMock(return_value=ToolResult(success=True, data={"logs": []}))
    workflow.control_plane_tool.query_incidents = AsyncMock(return_value=ToolResult(success=True, data={"incidents": []}))

    await workflow.execute(session_id, request, "deployment")
    final_status = DiagnosticStatus.model_validate_json(await redis_client.get(str(session_id)))
    
    assert final_status.status == "completed"
    assert any("Prometheus" in f.source for f in final_status.result.findings)
    assert "PrometheusQueryTool" in final_status.result.tools_used
    assert "LokiLogQueryTool" not in final_status.result.tools_used

@pytest.mark.asyncio
async def test_workflow_catastrophic_failure(workflow, mock_redis_client):
    """測試當工作流程本身發生未預期錯誤時的場景。"""
    redis_client, redis_store = mock_redis_client
    session_id = uuid.uuid4()
    request = DiagnosticRequest(incident_id="test-003", severity="P0", affected_services=["critical-service"])
    initial_status = DiagnosticStatus(session_id=session_id, status="processing", progress=10, current_step="start")
    redis_store[str(session_id)] = initial_status.model_dump_json()

    with patch.object(workflow, '_diagnose_deployment', new_callable=AsyncMock) as mock_diagnose:
        mock_diagnose.side_effect = ValueError("Something broke badly")
        await workflow.execute(session_id, request, "deployment")

    final_status = DiagnosticStatus.model_validate_json(await redis_client.get(str(session_id)))
    assert final_status.status == "failed"
    assert "Something broke badly" in final_status.error

@pytest.mark.asyncio
async def test_diagnose_alerts_stub(workflow, mock_redis_client):
    """
    測試告警診斷流程 (目前為存根)。
    """
    redis_client, redis_store = mock_redis_client
    session_id = uuid.uuid4()
    request = AlertAnalysisRequest(alert_ids=["alert-123"])
    initial_status = DiagnosticStatus(session_id=session_id, status="processing")
    redis_store[str(session_id)] = initial_status.model_dump_json()

    await workflow.execute(session_id, request, "alert_analysis")

    final_status = DiagnosticStatus.model_validate_json(await redis_client.get(str(session_id)))

    assert final_status.status == "completed"
    assert final_status.result is not None
    assert "尚未完全實作" in final_status.result.summary

@pytest.mark.asyncio
@pytest.mark.parametrize(
    "query, expected_tool, expected_service",
    [
        ("show me the cpu for auth-service", "prometheus", "auth-service"),
        ("get logs for billing-api", "loki", "billing-api"),
        ("any new deployments in payment-gateway?", "control_plane", "payment-gateway"),
        ("what is the meaning of life", None, None),
    ]
)
async def test_execute_query_routing(workflow, query, expected_tool, expected_service):
    """
    測試 _execute_query 方法是否能根據查詢關鍵字正確路由到對應的工具。
    """
    session_id = uuid.uuid4()
    request = ExecuteRequest(query=query)
    status = DiagnosticStatus(session_id=session_id, status="processing")

    # 模擬所有工具
    workflow.prometheus_tool.execute = AsyncMock(return_value=ToolResult(success=True, data={}))
    workflow.loki_tool.execute = AsyncMock(return_value=ToolResult(success=True, data={}))
    workflow.control_plane_tool.query_audit_logs = AsyncMock(return_value=ToolResult(success=True, data={}))

    result = await workflow._execute_query(session_id, request, status)

    if expected_tool == "prometheus":
        workflow.prometheus_tool.execute.assert_called_once()
        assert workflow.prometheus_tool.execute.call_args[0][0]["service"] == expected_service
        workflow.loki_tool.execute.assert_not_called()
        workflow.control_plane_tool.query_audit_logs.assert_not_called()
    elif expected_tool == "loki":
        workflow.loki_tool.execute.assert_called_once()
        assert workflow.loki_tool.execute.call_args[0][0]["service"] == expected_service
        workflow.prometheus_tool.execute.assert_not_called()
        workflow.control_plane_tool.query_audit_logs.assert_not_called()
    elif expected_tool == "control_plane":
        workflow.control_plane_tool.query_audit_logs.assert_called_once()
        assert workflow.control_plane_tool.query_audit_logs.call_args[0][0]["search"] == expected_service
        workflow.prometheus_tool.execute.assert_not_called()
        workflow.loki_tool.execute.assert_not_called()
    else: # 無法理解的查詢
        assert "無法理解查詢" in result.summary
        workflow.prometheus_tool.execute.assert_not_called()
        workflow.loki_tool.execute.assert_not_called()
        workflow.control_plane_tool.query_audit_logs.assert_not_called()

@pytest.mark.asyncio
async def test_analyze_capacity_workflow(workflow):
    """
    測試容量分析工作流程的成功路徑。
    """
    session_id = uuid.uuid4()
    resource_id = "res-123"
    service_name = "billing-service"
    request = CapacityAnalysisRequest(resource_ids=[resource_id], metric_type="cpu", forecast_days=30)
    status = DiagnosticStatus(session_id=session_id, status="processing")

    # 模擬 ControlPlaneTool 的回傳值
    mock_resource_data = {"id": resource_id, "name": service_name, "type": "deployment", "status": "running", "createdAt": "2023-01-01T00:00:00Z", "updatedAt": "2023-01-01T00:00:00Z"}
    workflow.control_plane_tool.get_resource_details = AsyncMock(
        return_value=ToolResult(success=True, data=mock_resource_data)
    )

    # 模擬 PrometheusTool 的回傳值
    mock_metrics_data = {"cpu_usage": "91.5%", "memory_usage": "75.2%"}
    workflow.prometheus_tool.execute = AsyncMock(
        return_value=ToolResult(success=True, data=mock_metrics_data)
    )

    # 執行分析
    response = await workflow._analyze_capacity(session_id, request, status)

    # 驗證回傳結果
    assert response.current_usage.peak == 91.5
    assert response.current_usage.average == 75.2
    assert len(response.recommendations) == 1
    recommendation = response.recommendations[0]
    assert recommendation.type == "scale_up"
    assert recommendation.resource == resource_id
    assert "CPU 使用率" in recommendation.reasoning

    # 驗證工具是否被正確呼叫
    workflow.control_plane_tool.get_resource_details.assert_called_once_with(resource_id)
    workflow.prometheus_tool.execute.assert_called_once_with(
        {"service": service_name, "metric_type": "saturation"}
    )
