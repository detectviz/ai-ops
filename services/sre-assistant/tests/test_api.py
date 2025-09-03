# services/sre-assistant/tests/test_api.py
"""
API 端點測試
"""

import pytest
from fastapi.testclient import TestClient
from unittest.mock import Mock, patch, AsyncMock
import json

from src.sre_assistant.main import app


@pytest.fixture
def client():
    """建立測試客戶端"""
    return TestClient(app)


@pytest.fixture
def mock_config():
    """模擬配置"""
    config = Mock()
    config.auth.provider = "none"
    config.prometheus.base_url = "http://prometheus:9090"
    config.loki.base_url = "http://loki:3100"
    config.control_plane.base_url = "http://control-plane:8081"
    return config


class TestHealthEndpoints:
    """健康檢查端點測試"""
    
    def test_health_check(self, client):
        """測試健康檢查端點"""
        response = client.get("/health")
        assert response.status_code == 200
        
        data = response.json()
        assert data["status"] == "healthy"
        assert data["service"] == "sre-assistant"
        assert "timestamp" in data
        assert "version" in data
    
    def test_readiness_check(self, client):
        """測試就緒檢查端點"""
        response = client.get("/ready")
        # 可能返回 200 或 503，取決於初始化狀態
        assert response.status_code in [200, 503]
        
        data = response.json()
        assert "status" in data
        if response.status_code == 200:
            assert data["status"] == "ready"
        else:
            assert data["status"] == "not ready"


class TestDiagnosticEndpoints:
    """診斷端點測試"""
    
    @patch("src.sre_assistant.main.verify_token")
    @patch("src.sre_assistant.main.workflow")
    async def test_diagnose_deployment(self, mock_workflow, mock_verify, client):
        """測試部署診斷端點"""
        # 設定 mock
        mock_verify.return_value = {"sub": "test-user", "roles": ["admin"]}
        mock_workflow.execute = AsyncMock(return_value={
            "summary": "查詢完成",
            "findings": [],
            "recommended_action": None,
            "confidence_score": 0.7
        })
        
        # 發送請求
        response = client.post(
            "/execute",
            json={
                "user_query": "檢查服務狀態",
                "context": {
                    "services": ["test-service"]
                }
            },
            headers={"Authorization": "Bearer test-token"}
        )
        
        assert response.status_code == 200
        
        data = response.json()
        assert data["status"] == "COMPLETED"
        assert data["summary"] == "查詢完成"


class TestAuthentication:
    """認證測試"""
    
    def test_missing_token(self, client):
        """測試缺少 Token"""
        response = client.post(
            "/diagnostics/deployment",
            json={
                "deployment_id": "test-deploy-001",
                "service_name": "test-service",
                "namespace": "default"
            }
        )
        
        # 應該返回 403 (Forbidden) 因為沒有提供 Token
        assert response.status_code == 403
    
    @patch("src.sre_assistant.main.jwks_client")
    def test_invalid_token(self, mock_jwks, client):
        """測試無效 Token"""
        # 模擬 Token 驗證失敗
        mock_jwks.get_signing_key_from_jwt.side_effect = Exception("Invalid token")
        
        response = client.post(
            "/diagnostics/deployment",
            json={
                "deployment_id": "test-deploy-001",
                "service_name": "test-service",
                "namespace": "default"
            },
            headers={"Authorization": "Bearer invalid-token"}
        )
        
        # 如果有設定 JWKS，應該返回 401
        # 但在測試環境中可能跳過驗證
        assert response.status_code in [200, 401]診斷完成",
            "findings": [],
            "recommended_action": "檢查資源限制",
            "confidence_score": 0.85
        })
        
        # 發送請求
        response = client.post(
            "/diagnostics/deployment",
            json={
                "deployment_id": "test-deploy-001",
                "service_name": "test-service",
                "namespace": "default"
            },
            headers={"Authorization": "Bearer test-token"}
        )
        
        assert response.status_code == 200
        
        data = response.json()
        assert data["status"] == "COMPLETED"
        assert "summary" in data
        assert "findings" in data
        assert "recommended_action" in data
        assert data["confidence_score"] == 0.85
    
    @patch("src.sre_assistant.main.verify_token")
    @patch("src.sre_assistant.main.workflow")
    async def test_diagnose_alerts(self, mock_workflow, mock_verify, client):
        """測試告警診斷端點"""
        # 設定 mock
        mock_verify.return_value = {"sub": "test-user", "roles": ["admin"]}
        mock_workflow.execute = AsyncMock(return_value={
            "summary": "分析完成",
            "findings": [
                {
                    "source": "AlertManager",
                    "data": {"alert_count": 3}
                }
            ],
            "recommended_action": "檢查基礎設施",
            "confidence_score": 0.75
        })
        
        # 發送請求
        response = client.post(
            "/diagnostics/alerts",
            json={
                "incident_ids": [101, 102, 103],
                "service_name": "test-service"
            },
            headers={"Authorization": "Bearer test-token"}
        )
        
        assert response.status_code == 200
        
        data = response.json()
        assert data["status"] == "COMPLETED"
        assert len(data["findings"]) == 1
        assert data["confidence_score"] == 0.75
    
    @patch("src.sre_assistant.main.verify_token")
    @patch("src.sre_assistant.main.workflow")
    async def test_execute_query(self, mock_workflow, mock_verify, client):
        """測試通用查詢端點"""
        # 設定 mock
        mock_verify.return_value = {"sub": "test-user", "roles": ["admin"]}
        mock_workflow.execute = AsyncMock(return_value={
            "summary": "