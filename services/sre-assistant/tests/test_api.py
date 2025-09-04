# services/sre-assistant/tests/test_api.py
"""
API 端點測試
"""

import pytest
from fastapi.testclient import TestClient
from unittest.mock import Mock, patch, AsyncMock
import json

# 確保在 app 匯入前設定環境變數，以進入測試模式
import os
os.environ["TESTING_MODE"] = "true"

from sre_assistant.main import app, verify_token


# 為了測試方便，我們覆寫 `verify_token` 的依賴
# 這樣可以隔離認證邏輯，專注於端點本身的測試
async def override_verify_token():
    return {"sub": "test-user", "roles": ["admin"]}

app.dependency_overrides[verify_token] = override_verify_token


@pytest.fixture
def client():
    """建立測試客戶端"""
    with TestClient(app) as c:
        yield c


@pytest.fixture
def mock_config():
    """模擬配置"""
    config = Mock()
    config.auth.provider = "jwt"  # 強制使用 jwt 供測試
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
        # 在測試模式下，依賴應該是就緒的
        response = client.get("/ready")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ready"


class TestDiagnosticEndpoints:
    """診斷端點測試"""

    @patch("sre_assistant.main.workflow")
    def test_diagnose_deployment(self, mock_workflow, client):
        """測試部署診斷成功"""
        # 設定 mock
        mock_workflow.execute = AsyncMock(return_value={
            "summary": "診斷完成",
            "findings": [],
            "recommended_action": "檢查資源限制",
            "confidence_score": 0.85
        })

        # 發送請求
        response = client.post(
            "/diagnostics/deployment",
            json={
                "context": {
                    "deployment_id": "test-deploy-001",
                    "service_name": "test-service",
                    "namespace": "default"
                }
            },
            headers={"Authorization": "Bearer test-token"} # 即使有覆寫，也帶上 header
        )

        assert response.status_code == 200

        data = response.json()
        assert data["status"] == "COMPLETED"
        assert data["summary"] == "診斷完成"
        assert data["confidence_score"] == 0.85

    @patch("sre_assistant.main.workflow")
    def test_diagnose_alerts(self, mock_workflow, client):
        """測試告警診斷端點"""
        # 設定 mock
        mock_workflow.execute = AsyncMock(return_value={
            "summary": "分析完成",
            "findings": [{"source": "AlertManager", "data": {"alert_count": 3}}],
            "recommended_action": "檢查基礎設施",
            "confidence_score": 0.75
        })
        
        # 發送請求
        response = client.post(
            "/diagnostics/alerts",
            json={
                "context": {
                    "incident_ids": [101, 102, 103],
                    "service_name": "test-service"
                }
            },
            headers={"Authorization": "Bearer test-token"}
        )
        
        assert response.status_code == 200
        
        data = response.json()
        assert data["status"] == "COMPLETED"
        assert len(data["findings"]) == 1
        assert data["confidence_score"] == 0.75


class TestAuthentication:
    """認證邏輯的獨立測試"""

    # 移除全域的依賴覆寫，以便單獨測試認證
    @pytest.fixture(autouse=True)
    def unpatch_verify_token(self):
        app.dependency_overrides = {}
        yield
        app.dependency_overrides = {}

    def test_missing_token(self, client):
        """測試在需要認證時缺少 Token"""
        # 使用一個 mock jwks_client 來強制觸發認證邏輯
        with patch("sre_assistant.main.jwks_client", new=Mock()):
            response = client.post(
                "/diagnostics/deployment",
                json={
                    "context": {
                        "deployment_id": "test-deploy-001",
                        "service_name": "test-service",
                        "namespace": "default"
                    }
                }
            )
            # 在 main.py 中，如果 jwks_client 存在但 header 不存在，會返回 401
            assert response.status_code == 401
            assert "缺少認證憑證" in response.text

    def test_invalid_token(self, client):
        """測試提供了無效的 Token"""
        # 建立一個會引發錯誤的 mock jwks_client
        from jwt import InvalidTokenError
        mock_jwks = Mock()
        mock_jwks.get_signing_key_from_jwt.side_effect = InvalidTokenError("Invalid token signature")

        with patch("sre_assistant.main.jwks_client", new=mock_jwks):
            response = client.post(
                "/diagnostics/deployment",
                json={
                    "context": {
                        "deployment_id": "test-deploy-001",
                        "service_name": "test-service",
                        "namespace": "default"
                    }
                },
                headers={"Authorization": "Bearer invalid-token"}
            )

            assert response.status_code == 401
            assert "無效的 Token" in response.text
