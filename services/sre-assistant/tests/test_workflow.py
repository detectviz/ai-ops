"""
SRE 工作流程測試 (已重構以匹配目前的實作)
"""

import pytest
import uuid
from unittest.mock import Mock, AsyncMock, patch

from sre_assistant.workflow import SREWorkflow
from sre_assistant.contracts import (
    DiagnosticRequest,
    ToolResult,
    ToolError,
    DiagnosticStatus,
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
def workflow(mock_config, mock_redis_client):
    """建立一個帶有模擬依賴的工作流程實例"""
    redis_client, _ = mock_redis_client
    return SREWorkflow(mock_config, redis_client)


@pytest.mark.asyncio
async def test_diagnose_deployment_success_e2e(workflow, mock_redis_client):
    """
    測試一個成功的部署診斷流程 (端到端)。
    
    此測試已更新，以反映對 ControlPlaneTool 的具體方法呼叫。
    
    驗證：
    - 所有工具的具體方法都被正確呼叫。
    - 任務狀態在 Redis 中被正確更新。
    - 最終的 DiagnosticResult 包含來自所有工具的綜合、具體的調查發現。
    """
    redis_client, redis_store = mock_redis_client
    session_id = uuid.uuid4()
    service_name = "test-service"
    request = DiagnosticRequest(
        incident_id="test-001",
        severity="P2",
        affected_services=[service_name]
    )
    
    # 準備初始狀態
    initial_status = DiagnosticStatus(session_id=session_id, status="processing", progress=10, current_step="start")
    redis_store[str(session_id)] = initial_status.model_dump_json()

    # --- 模擬工具的回傳值 ---
    # 讓每個工具回傳一些可以觸發 "Finding" 的數據
    workflow.prometheus_tool.execute = AsyncMock(return_value=ToolResult(
        success=True, data={"cpu_usage": "95%"}
    ))
    workflow.loki_tool.execute = AsyncMock(return_value=ToolResult(
        success=True, data={"analysis": {"critical_indicators": ["發現 5 次 OOMKilled"]}}
    ))
    # 模擬 ControlPlaneTool 的具體方法
    workflow.control_plane_tool.query_audit_logs = AsyncMock(return_value=ToolResult(
        success=True, data={"logs": [{"user": "test-user", "action": "deploy"}]}
    ))
    workflow.control_plane_tool.query_incidents = AsyncMock(return_value=ToolResult(
        success=True, data={"incidents": [{"id": "INC-999", "title": "Related DB issue"}]}
    ))

    # --- 執行工作流程 ---
    await workflow.execute(session_id, request, "deployment")

    # --- 驗證結果 ---
    final_status_json = await redis_client.get(str(session_id))
    assert final_status_json is not None
    final_status = DiagnosticStatus.model_validate_json(final_status_json)
    
    # 驗證最終狀態
    assert final_status.status == "completed"
    assert final_status.progress == 100
    assert final_status.result is not None
    
    # 驗證所有工具都被呼叫
    workflow.prometheus_tool.execute.assert_called_once()
    workflow.loki_tool.execute.assert_called_once()
    workflow.control_plane_tool.query_audit_logs.assert_called_once()
    workflow.control_plane_tool.query_incidents.assert_called_once()
    
    # 驗證調查發現 (Findings)
    findings = final_status.result.findings
    assert len(findings) == 4  # 預期來自 4 個工具呼叫的 4 個發現

    prometheus_finding = next((f for f in findings if f.source == "Prometheus"), None)
    assert prometheus_finding is not None
    assert "CPU 使用率過高" in prometheus_finding.message

    loki_finding = next((f for f in findings if f.source == "Loki"), None)
    assert loki_finding is not None
    assert "OOMKilled" in loki_finding.message

    cp_audit_finding = next((f for f in findings if f.source == "Control-Plane" and "審計日誌" in f.message), None)
    assert cp_audit_finding is not None
    assert cp_audit_finding.severity == "info"

    cp_incident_finding = next((f for f in findings if f.source == "Control-Plane" and "活躍事件" in f.message), None)
    assert cp_incident_finding is not None
    assert cp_incident_finding.severity == "warning"

    # 驗證使用的工具列表
    assert "PrometheusQueryTool" in final_status.result.tools_used
    assert "LokiLogQueryTool" in final_status.result.tools_used
    assert "ControlPlaneTool (Audit)" in final_status.result.tools_used
    assert "ControlPlaneTool (Incidents)" in final_status.result.tools_used


@pytest.mark.asyncio
async def test_diagnose_deployment_with_tool_failure(workflow, mock_redis_client):
    """測試當一個工具執行失敗時的場景。"""
    redis_client, redis_store = mock_redis_client
    session_id = uuid.uuid4()
    request = DiagnosticRequest(incident_id="test-002", severity="P1", affected_services=["failing-service"])
    initial_status = DiagnosticStatus(session_id=session_id, status="processing", progress=10, current_step="start")
    redis_store[str(session_id)] = initial_status.model_dump_json()

    # Mock 工具，其中 Loki 會失敗
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
async def test_diagnose_alerts_success(workflow, mock_redis_client):
    """
    測試一個成功的告警診斷流程。

    驗證：
    - `query_incidents` 被正確呼叫。
    - `loki_tool.execute` 被呼叫以獲取相關日誌。
    - 最終結果包含來自所有工具的綜合發現。
    """
    from sre_assistant.contracts import AlertAnalysisRequest
    from datetime import datetime, timezone

    redis_client, redis_store = mock_redis_client
    session_id = uuid.uuid4()
    alert_id = "alert-123"
    request = AlertAnalysisRequest(alert_ids=[alert_id])

    initial_status = DiagnosticStatus(session_id=session_id, status="processing", progress=10, current_step="start")
    redis_store[str(session_id)] = initial_status.model_dump_json()

    # --- 模擬工具的回傳值 ---
    mock_incident_data = {
        "incidents": [{
            "id": alert_id,
            "title": "CPU High",
            "service_name": "billing-service",
            "created_at": datetime.now(timezone.utc).isoformat(),
            "details": {"prometheus_query": "cpu_usage > 90"}
        }]
    }
    workflow.control_plane_tool.query_incidents = AsyncMock(
        return_value=ToolResult(success=True, data=mock_incident_data)
    )
    workflow.loki_tool.execute = AsyncMock(
        return_value=ToolResult(success=True, data={"logs": [{"line": "error connecting to db"}]})
    )
    workflow.prometheus_tool.execute = AsyncMock(
        return_value=ToolResult(success=True, data={"value": [162, "99.5"]})
    )

    # --- 執行工作流程 ---
    await workflow.execute(session_id, request, "alert_analysis")

    # --- 驗證結果 ---
    final_status = DiagnosticStatus.model_validate_json(await redis_client.get(str(session_id)))

    assert final_status.status == "completed"
    assert final_status.result is not None

    # 驗證所有工具都被呼叫
    workflow.control_plane_tool.query_incidents.assert_called_once_with(params={'search': alert_id, 'limit': 1})
    workflow.loki_tool.execute.assert_called_once()
    workflow.prometheus_tool.execute.assert_called_once()

    # 驗證調查發現 (Findings)
    findings = final_status.result.findings
    assert len(findings) == 3 # 1 from CP, 1 from Loki, 1 from Prometheus
    assert any("正在調查告警" in f.message for f in findings)
    assert any("發現 1 條日誌" in f.message for f in findings)
    assert any("執行告警相關的 Prometheus 查詢成功" in f.message for f in findings)

    # 驗證使用的工具列表
    assert "ControlPlaneTool (Incidents)" in final_status.result.tools_used
    assert "LokiLogQueryTool" in final_status.result.tools_used
    assert "PrometheusQueryTool" in final_status.result.tools_used


@pytest.mark.asyncio
async def test_diagnose_alerts_cp_failure(workflow, mock_redis_client):
    """
    測試當 Control Plane 工具無法獲取告警詳情時的場景。
    """
    from sre_assistant.contracts import AlertAnalysisRequest

    redis_client, redis_store = mock_redis_client
    session_id = uuid.uuid4()
    alert_id = "alert-456"
    request = AlertAnalysisRequest(alert_ids=[alert_id])

    initial_status = DiagnosticStatus(session_id=session_id, status="processing", progress=10, current_step="start")
    redis_store[str(session_id)] = initial_status.model_dump_json()

    # --- 模擬工具的回傳值 ---
    # Control Plane 查詢失敗
    workflow.control_plane_tool.query_incidents = AsyncMock(
        return_value=ToolResult(success=False, error=ToolError(code="API_ERROR", message="Not Found"))
    )
    workflow.loki_tool.execute = AsyncMock()
    workflow.prometheus_tool.execute = AsyncMock()

    # --- 執行工作流程 ---
    await workflow.execute(session_id, request, "alert_analysis")

    # --- 驗證結果 ---
    final_status = DiagnosticStatus.model_validate_json(await redis_client.get(str(session_id)))

    assert final_status.status == "completed"
    assert final_status.result is not None

    # Loki 和 Prometheus 不應該被呼叫
    workflow.loki_tool.execute.assert_not_called()
    workflow.prometheus_tool.execute.assert_not_called()

    # 應該有一條警告性質的 Finding
    findings = final_status.result.findings
    assert len(findings) == 1
    assert findings[0].severity == "warning"
    assert f"無法獲取 ID 為 {alert_id} 的告警詳情" in findings[0].message
