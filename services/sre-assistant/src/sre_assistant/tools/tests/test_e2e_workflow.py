# services/sre-assistant/tests/test_e2e_workflow.py
"""
端到端 (E2E) 工作流程整合測試
"""

import pytest
from unittest.mock import patch, AsyncMock

from sre_assistant.workflow import SREWorkflow
from sre_assistant.contracts import SRERequest, SeverityLevel

# 使用來自 conftest.py 或其他測試文件的共享 fixture


@pytest.mark.asyncio
@patch('sre_assistant.tools.control_plane_tool.ControlPlaneTool.get_audit_logs', new_callable=AsyncMock)
@patch('sre_assistant.tools.loki_tool.LokiLogQueryTool.query_logs_by_service', new_callable=AsyncMock)
@patch('sre_assistant.tools.prometheus_tool.PrometheusQueryTool.query_golden_signals', new_callable=AsyncMock)
async def test_e2e_deployment_diagnosis_workflow(
    mock_prometheus_tool,
    mock_loki_tool,
    mock_control_plane_tool,
    workflow: SREWorkflow
):
    """
    測試一個完整的部署診斷端到端流程。
    此測試驗證 SREWorkflow 是否能正確地協調所有工具。
    """
    # --- 1. 設定模擬資料 ---
    
    # 模擬 Prometheus 回應
    mock_prometheus_tool.return_value = {
        "latency_p99": "2500ms",
        "error_rate": "5.00%",
        "cpu_usage": "95.00%",
        "memory_usage": "98.00%" # 模擬高記憶體使用
    }
    
    # 模擬 Loki 回應
    mock_loki_tool.return_value = {
        "total_logs": 1,
        "level_distribution": {"ERROR": 1},
        "error_types": {"OOMKilled": 1},
        "top_errors": [{"pattern": "OOMKilled", "count": 1}],
        "critical_indicators": ["發現 1 次記憶體不足錯誤 (OOMKilled)"]
    }
    
    # 模擬 Control Plane 回應
    mock_control_plane_tool.return_value = [
        {"time": "2025-01-10T10:00:00Z", "user": "testuser", "action": "DEPLOY"}
    ]
    
    # --- 2. 準備請求 ---
    
    request = SRERequest(
        incident_id="e2e-test-001",
        severity=SeverityLevel.P0,
        input="部署失敗，請診斷",
        affected_services=["critical-service"],
        context={
            "type": "deployment_diagnosis",
            "service_name": "critical-service",
            "namespace": "production",
        }
    )
    
    # --- 3. 執行工作流程 ---
    
    result = await workflow.execute(request)
    
    # --- 4. 驗證 ---
    
    # 驗證所有工具都被正確調用一次
    mock_prometheus_tool.assert_called_once_with(
        service_name="critical-service",
        namespace="production",
        duration="5m"
    )
    mock_loki_tool.assert_called_once_with(
        service_name="critical-service",
        namespace="production",
        level="error",
        duration="5m"
    )
    mock_control_plane_tool.assert_called_once_with(
        service_name="critical-service",
        limit=5
    )
    
    # 驗證最終報告的內容
    assert result["status"] == "COMPLETED"
    
    # 驗證 findings，這比檢查 summary 字串更可靠
    assert len(result["findings"]) == 4 # CPU, Memory, Loki, Audit
    
    finding_sources = {f["source"] for f in result["findings"]}
    assert "Prometheus" in finding_sources
    assert "Loki" in finding_sources
    assert "Control-Plane" in finding_sources
    
    # 驗證建議
    assert "增加記憶體限制" in result["recommended_action"]
    assert "增加 CPU 限制" in result["recommended_action"]
    assert "審查最近的配置變更" in result["recommended_action"]
    
    # 驗證信心分數
    assert result["confidence_score"] > 0.8
    
    print("✅ E2E 部署診斷流程測試成功")
