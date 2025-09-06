"""
API 端點測試 (已重構以匹配目前的實作)
"""

import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, AsyncMock
import uuid

# 確保在 app 匯入前設定環境變數
import os
os.environ["ENVIRONMENT"] = "test"

from sre_assistant.main import app, verify_token

# 全域覆寫 JWT 驗證，用於大部分的端點測試
async def override_verify_token():
    return {"sub": "test-user", "roles": ["admin"]}

app.dependency_overrides[verify_token] = override_verify_token


@pytest.fixture(scope="function")
def client(mocker):
    """
    為每個測試建立一個新的 TestClient 實例。

    透過模擬 redis.from_url 來防止在測試期間嘗試連接真實的 Redis，
    從而確保應用程式的 lifespan 能夠成功完成，並使 /readyz 端點通過。
    """
    # 模擬 redis.from_url 回傳一個可用的 AsyncMock 物件
    mock_redis_client = AsyncMock()
    mock_redis_client.ping = AsyncMock() # 確保 ping() 是可 await 的
    mocker.patch('sre_assistant.main.redis.from_url', return_value=mock_redis_client)

    # 現在，當 TestClient 初始化 app 時，lifespan 會使用模擬的 redis client
    with TestClient(app) as c:
        yield c

class TestHealthEndpoints:
    """健康檢查端點測試"""

    def test_health_check(self, client):
        """測試 /healthz 端點"""
        response = client.get("/healthz")
        # 在測試啟動失敗的情況下，這裡會是 404
        # 在測試啟動成功的情況下，應該是 200
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"

    def test_readiness_check(self, client):
        """測試 /readyz 端點"""
        response = client.get("/readyz")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ready"

    def test_metrics_endpoint(self, client):
        """測試 /api/v1/metrics 端點"""
        response = client.get("/api/v1/metrics")
        assert response.status_code == 200
        assert "text/plain" in response.headers["content-type"]
        # 檢查一些預期的指標是否存在
        assert "python_info" in response.text


class TestDiagnosticEndpoints:
    """非同步診斷端點測試"""

    @patch("sre_assistant.main.run_workflow_bg", new_callable=AsyncMock)
    def test_diagnose_deployment_accepted(self, mock_run_workflow_bg, client):
        """測試 /diagnostics/deployment 端點是否能正確接受任務"""
        request_data = {
            "incident_id": "INC-123",
            "severity": "P1",
            "affected_services": ["auth-service"],
        }
        response = client.post("/api/v1/diagnostics/deployment", json=request_data)

        assert response.status_code == 202
        data = response.json()
        assert data["status"] == "accepted"
        assert "session_id" in data
        
        # 驗證背景任務是否被呼叫
        mock_run_workflow_bg.assert_called_once()
        # 驗證呼叫時的參數
        call_args = mock_run_workflow_bg.call_args[0]
        assert isinstance(call_args[0], uuid.UUID) # session_id
        assert call_args[1].incident_id == "INC-123" # request object
        assert call_args[2] == "deployment" # request_type

    @patch("sre_assistant.main.redis_client")
    async def test_get_diagnostic_status_found(self, mock_redis, client):
        """測試成功獲取任務狀態"""
        session_id = uuid.uuid4()
        # 模擬 Redis 返回的 JSON 資料
        mock_status_json = {
            "session_id": str(session_id),
            "status": "processing",
            "progress": 50,
            "current_step": "正在執行工具"
        }
        mock_redis.get = AsyncMock(return_value=str(mock_status_json).replace("'", '"'))

        response = client.get(f"/api/v1/diagnostics/{session_id}/status")
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "processing"
        assert data["progress"] == 50
        mock_redis.get.assert_called_once_with(str(session_id))

    @patch("sre_assistant.main.redis_client")
    async def test_get_diagnostic_status_not_found(self, mock_redis, client):
        """測試查詢不存在的任務狀態"""
        session_id = uuid.uuid4()
        mock_redis.get = AsyncMock(return_value=None)

        response = client.get(f"/api/v1/diagnostics/{session_id}/status")

        assert response.status_code == 404
        assert "找不到指定的診斷任務" in response.text


class TestAuthentication:
    """測試 JWT 認證邏輯"""

    @pytest.fixture(autouse=True)
    def setup_auth(self):
        """為這個測試類別移除全域的 token 覆寫"""
        app.dependency_overrides = {}
        yield
        # 測試結束後恢復
        app.dependency_overrides[verify_token] = override_verify_token

    def test_missing_token(self, client):
        """測試在需要認證時缺少 Token 的情況"""
        response = client.post("/api/v1/diagnostics/deployment", json={})
        # Per FastAPI's HTTPBearer, a missing header results in a 403 Forbidden, not 401.
        assert response.status_code == 403
        assert "Not authenticated" in response.text

    @patch("sre_assistant.main.fetch_jwks")
    def test_invalid_token_structure(self, mock_fetch_jwks, client):
        """測試提供了無效結構的 Token (非 Bearer)"""
        # 即使 JWKS 正確，token 格式錯誤也應該失敗
        mock_fetch_jwks.return_value = [{"kid": "test-kid"}]

        response = client.post(
            "/api/v1/diagnostics/deployment",
            json={},
            headers={"Authorization": "InvalidScheme some-token"}
        )
        # An invalid scheme also results in a 403 from HTTPBearer
        assert response.status_code == 403
        assert "Invalid authentication credentials" in response.text
