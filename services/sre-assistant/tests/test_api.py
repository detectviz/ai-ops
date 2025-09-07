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
def client_with_redis(mocker):
    """
    提供一個 TestClient 和一個與之關聯的、可操作的 Redis 模擬儲存。
    這對於需要直接操作 Redis 狀態的端到端測試非常有用。
    """
    redis_store = {}

    async def get(key):
        return redis_store.get(key)

    async def set(key, value, ex=None):
        redis_store[key] = value
        return True
    
    mock_redis_client = AsyncMock()
    mock_redis_client.ping.return_value = True
    mock_redis_client.get.side_effect = get
    mock_redis_client.set.side_effect = set

    mocker.patch('sre_assistant.main.redis.from_url', return_value=mock_redis_client)
    
    with TestClient(app) as c:
        yield c, redis_store

@pytest.fixture(scope="function")
def client(client_with_redis):
    """一個標準的 TestClient，不直接暴露 Redis store。"""
    c, _ = client_with_redis
    yield c

class TestHealthEndpoints:
    """健康檢查端點測試"""

    def test_health_check(self, client):
        """測試 /api/v1/healthz 端點（契約：HealthStatus）"""
        response = client.get("/api/v1/healthz")
        assert response.status_code == 200
        data = response.json()
        # 狀態應為 healthy/unhealthy
        assert data["status"] in ("healthy", "unhealthy")
        assert isinstance(data.get("timestamp"), str)
        # 允許 version/uptime 為可選欄位

    def test_readiness_check(self, client):
        """測試 /api/v1/readyz 端點（契約：ReadinessStatus）"""
        response = client.get("/api/v1/readyz")
        # 允許 200（就緒）或 503（未就緒）
        assert response.status_code in (200, 503)
        data = response.json()
        assert isinstance(data.get("ready"), bool)
        assert isinstance(data.get("checks"), dict)
        for k in ("prometheus", "loki", "control_plane"):
            assert k in data["checks"], f"缺少 checks['{k}']"
            assert isinstance(data["checks"][k], bool)

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
        sessionId = uuid.uuid4()
        # 模擬 Redis 返回的 JSON 資料
        mock_status_json = {
            "session_id": str(sessionId),
            "status": "processing",
            "progress": 50,
            "current_step": "正在執行工具"
        }
        mock_redis.get = AsyncMock(return_value=str(mock_status_json).replace("'", '"'))

        response = client.get(f"/api/v1/diagnostics/{sessionId}/status")
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "processing"
        assert data["progress"] == 50
        mock_redis.get.assert_called_once_with(str(sessionId))

    @patch("sre_assistant.main.redis_client")
    async def test_get_diagnostic_status_not_found(self, mock_redis, client):
        """測試查詢不存在的任務狀態"""
        sessionId = uuid.uuid4()
        mock_redis.get = AsyncMock(return_value=None)

        response = client.get(f"/api/v1/diagnostics/{sessionId}/status")

        assert response.status_code == 404
        assert "找不到指定的診斷任務" in response.text

    @patch("sre_assistant.main.run_workflow_bg", new_callable=AsyncMock)
    def test_async_task_status_polling(self, mock_run_workflow_bg, client_with_redis):
        """測試完整的非同步任務狀態輪詢流程"""
        client, redis_store = client_with_redis
        
        # 1. 啟動一個新任務
        request_data = {"incident_id": "INC-456", "severity": "P3", "affected_services": ["billing-api"]}
        response = client.post("/api/v1/diagnostics/deployment", json=request_data)
        assert response.status_code == 202
        task_info = response.json()
        sessionId = task_info["session_id"]
        
        # 2. 模擬背景工作流程更新 Redis 中的狀態 (第一次更新)
        status_step1 = {
            "session_id": sessionId, "status": "processing", "progress": 40,
            "current_step": "正在查詢 Prometheus 指標..."
        }
        redis_store[sessionId] = str(status_step1).replace("'", '"')
        
        # 3. 輪詢狀態端點，驗證第一次更新
        response = client.get(f"/api/v1/diagnostics/{sessionId}/status")
        assert response.status_code == 200
        status_data = response.json()
        assert status_data["progress"] == 40
        assert "Prometheus" in status_data["current_step"]
        
        # 4. 模擬背景工作流程再次更新 Redis (完成)
        status_step2 = {
            "session_id": sessionId, "status": "completed", "progress": 100,
            "current_step": "診斷完成", "result": {"summary": "發現 CPU 使用率過高"}
        }
        redis_store[sessionId] = str(status_step2).replace("'", '"')
        
        # 5. 再次輪詢，驗證最終狀態
        response = client.get(f"/api/v1/diagnostics/{sessionId}/status")
        assert response.status_code == 200
        final_data = response.json()
        assert final_data["status"] == "completed"
        assert final_data["result"]["summary"] == "發現 CPU 使用率過高"


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

    @patch("sre_assistant.auth.fetch_jwks")
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
