# services/sre-assistant/tests/test_workflow.py
"""
工作流程測試
"""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime, timezone

from src.sre_assistant.workflow import SREWorkflow
from src.sre_assistant.contracts import (
    SRERequest,
    ToolResult,
    ToolError,
    Finding,
    SeverityLevel
)


@pytest.fixture
def mock_config():
    """建立模擬配置"""
    config = Mock()
    config.workflow = {
        "parallel_diagnosis": True,
        "diagnosis_timeout_seconds": 60,
        "max_retries": 3
    }
    config.prometheus = {
        "base_url": "http://prometheus:9090",
        "timeout_seconds": 15
    }
    config.loki = {
        "base_url": "http://loki:3100",
        "timeout_seconds": 20
    }
    config.control_plane = {
        "base_url": "http://control-plane:8081",
        "timeout_seconds": 10
    }
    return config


@pytest.fixture
def workflow(mock_config):
    """建立工作流程實例"""
    return SREWorkflow(mock_config)


class TestSREWorkflow:
    """SRE 工作流程測試"""
    
    @pytest.mark.asyncio
    async def test_execute_deployment_diagnosis(self, workflow):
        """測試部署診斷執行"""
        # 建立請求
        request = SRERequest(
            incident_id="test-001",
            severity=SeverityLevel.P2,
            input="診斷部署問題",
            affected_services=["test-service"],
            context={
                "type": "deployment_diagnosis",
                "service_name": "test-service",
                "namespace": "default",
                "deployment_id": "deploy-123"
            }
        )
        
        # Mock 工具查詢方法
        workflow._query_metrics = AsyncMock(return_value=ToolResult(
            success=True,
            data={
                "cpu_usage": "95%",
                "memory_usage": "88%",
                "error_rate": "0.02",
                "latency_p99": "1200ms"
            }
        ))
        
        workflow._query_logs = AsyncMock(return_value=ToolResult(
            success=True,
            data={
                "error_count": 10,
                "critical_errors": ["OOMKilled"],
                "log_volume": "high"
            }
        ))
        
        workflow._query_audit_logs = AsyncMock(return_value=ToolResult(
            success=True,
            data={
                "recent_changes": [
                    {
                        "time": "2025-01-02T10:00:00Z",
                        "user": "admin",
                        "action": "UPDATE_CONFIG",
                        "details": "Changed memory limit"
                    }
                ]
            }
        ))
        
        # 執行工作流程
        result = await workflow.execute(request)
        
        # 驗證結果
        assert result["status"] == "COMPLETED"
        assert "summary" in result
        assert "findings" in result
        assert "recommended_action" in result
        assert "confidence_score" in result
        assert "execution_time_ms" in result
        
        # 驗證工具被調用
        workflow._query_metrics.assert_called_once()
        workflow._query_logs.assert_called_once()
        workflow._query_audit_logs.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_execute_alert_diagnosis(self, workflow):
        """測試告警診斷執行"""
        request = SRERequest(
            incident_id="alert-001",
            severity=SeverityLevel.P1,
            input="分析告警",
            affected_services=["service-a", "service-b"],
            context={
                "type": "alert_diagnosis",
                "incident_ids": [101, 102, 103]
            }
        )
        
        result = await workflow.execute(request)
        
        assert result["status"] == "COMPLETED"
        assert "分析了 3 個告警事件" in result["summary"]
    
    @pytest.mark.asyncio
    async def test_execute_with_error(self, workflow):
        """測試執行時發生錯誤"""
        request = SRERequest(
            incident_id="error-001",
            severity=SeverityLevel.P0,
            input="測試錯誤",
            affected_services=["test-service"],
            context={"type": "deployment_diagnosis"}
        )
        
        # Mock 工具查詢拋出異常
        workflow._query_metrics = AsyncMock(side_effect=Exception("連接失敗"))
        
        result = await workflow.execute(request)
        
        # 應該優雅地處理錯誤
        assert result["status"] == "FAILED"
        assert "診斷過程發生錯誤" in result["summary"]
        assert result["confidence_score"] == 0.0
    
    @pytest.mark.asyncio
    async def test_parallel_execution(self, workflow):
        """測試並行執行"""
        # 確保並行模式開啟
        workflow.parallel_diagnosis = True
        
        # Mock 工具查詢，每個需要不同時間
        async def slow_metrics(*args, **kwargs):
            await asyncio.sleep(0.1)
            return ToolResult(success=True, data={"metric": "value"})
        
        async def fast_logs(*args, **kwargs):
            await asyncio.sleep(0.01)
            return ToolResult(success=True, data={"log": "entry"})
        
        async def medium_audit(*args, **kwargs):
            await asyncio.sleep(0.05)
            return ToolResult(success=True, data={"audit": "log"})
        
        workflow._query_metrics = slow_metrics
        workflow._query_logs = fast_logs
        workflow._query_audit_logs = medium_audit
        
        request = SRERequest(
            incident_id="parallel-001",
            severity=SeverityLevel.P2,
            input="測試並行",
            affected_services=["test-service"],
            context={
                "type": "deployment_diagnosis",
                "service_name": "test-service"
            }
        )
        
        # 測量執行時間
        import time
        start = time.time()
        result = await workflow.execute(request)
        elapsed = time.time() - start
        
        # 並行執行應該比串行快
        # 串行需要 0.1 + 0.01 + 0.05 = 0.16 秒
        # 並行應該接近最慢的 0.1 秒
        assert elapsed < 0.15  # 留一些餘地
        assert result["status"] == "COMPLETED"
    
    def test_analyze_deployment_results(self, workflow):
        """測試結果分析"""
        results = {
            "prometheus": ToolResult(
                success=True,
                data={
                    "cpu_usage": "85%",
                    "memory_usage": "92%",
                    "error_rate": "0.1",
                    "latency_p99": "2000ms"
                }
            ),
            "loki": ToolResult(
                success=True,
                data={
                    "critical_errors": ["OOMKilled", "Connection timeout"],
                    "error_count": 50
                }
            ),
            "audit": ToolResult(
                success=True,
                data={
                    "recent_changes": [
                        {"action": "UPDATE_CONFIG", "user": "admin"}
                    ]
                }
            )
        }
        
        request = SRERequest(
            incident_id="test",
            severity=SeverityLevel.P2,
            input="test",
            affected_services=["test"]
        )
        
        analysis = workflow._analyze_deployment_results(results, request)
        
        assert analysis["status"] == "COMPLETED"
        assert "發現" in analysis["summary"]
        assert len(analysis["findings"]) > 0
        assert analysis["recommended_action"] is not None
        assert analysis["confidence_score"] > 0
    
    def test_generate_recommendation(self, workflow):
        """測試建議生成"""
        issues = [
            "OOMKilled",
            "CPU 使用率過高",
            "Connection timeout",
            "最近有配置變更"
        ]
        
        recommendation = workflow._generate_recommendation(issues)
        
        assert "增加記憶體限制" in recommendation
        assert "增加 CPU 限制" in recommendation
        assert "檢查網路連接" in recommendation
        assert "審查最近的配置變更" in recommendation
    
    def test_calculate_confidence(self, workflow):
        """測試信心分數計算"""
        # 沒有發現
        findings = []
        score = workflow._calculate_confidence(findings)
        assert score == 0.3
        
        # 有嚴重發現
        findings = [
            Finding(
                source="Test",
                severity=SeverityLevel.P0,
                data={},
                timestamp=datetime.now(timezone.utc)
            )
        ]
        score = workflow._calculate_confidence(findings)
        assert score == 1.0
        
        # 混合發現
        findings = [
            Finding(source="Test", severity=SeverityLevel.P1, data={}),
            Finding(source="Test", severity=SeverityLevel.P2, data={}),
            Finding(source="Test", severity=SeverityLevel.P3, data={})
        ]
        score = workflow._calculate_confidence(findings)
        assert 0 < score < 1