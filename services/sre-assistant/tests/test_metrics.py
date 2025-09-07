"""
Prometheus 指標端點契約測試
"""

from fastapi.testclient import TestClient
from sre_assistant.main import app


def test_metrics_endpoint_contract():
    """測試 /api/v1/metrics 端點是否回傳 text/plain 並有內容"""
    client = TestClient(app)
    resp = client.get("/api/v1/metrics")
    assert resp.status_code == 200
    # Content-Type 應為 text/plain; 允許包含編碼資訊
    assert resp.headers.get("content-type", "").startswith("text/plain")
    body = resp.content
    assert isinstance(body, (bytes, bytearray)) and len(body) > 0
    # 常見的 Prometheus exposition 格式包含 HELP/TYPE 行，非強制但可作弱驗證
    assert b"# HELP" in body or b"# TYPE" in body
