# 整合測試：驗證 SRE Assistant 與真實本地服務的端到端互動
#
# 執行前提：
# 1. 依照根目錄 Makefile 的指示，執行 `make start-services` 以啟動所有本地依賴服務
#    (Keycloak, PostgreSQL, Redis, VictoriaMetrics, ChromaDB)。
# 2. 確保 control-plane 和 sre-assistant 服務正在運行。
# 3. 設定環境變數 `INTEGRATION_TESTING=true` 以啟用此測試。
#
# 測試目的：
# - 驗證 SREWorkflow 是否能與真實的工具 (Prometheus, Loki, ControlPlane) 成功通訊。
# - 驗證 M2M 認證流程 (與 Keycloak) 是否正常運作。
# - 驗證任務狀態是否能正確地在 Redis 中被讀寫。
# - 確保端到端的 `/diagnostics/deployment` 流程能夠順利完成並產生有意義的結果。

import pytest
import os
import uuid
import asyncio
import redis.asyncio as aioredis

from sre_assistant.main import get_config_manager
from sre_assistant.workflow import SREWorkflow
from sre_assistant.contracts import DiagnosticRequest, DiagnosticStatus

# 只有當環境變數 INTEGRATION_TESTING 為 'true' 時才執行此模組的測試
pytestmark = pytest.mark.skipif(
    os.environ.get("INTEGRATION_TESTING", "false").lower() != "true",
    reason="整合測試需要啟動所有本地服務並設定 INTEGRATION_TESTING=true"
)


@pytest.fixture(scope="module")
def event_loop():
    """為整個模組提供一個事件循環"""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="module")
def config():
    """載入真實的開發環境設定"""
    # 假設 `get_config_manager` 能夠自動載入 `development.yaml`
    return get_config_manager()


@pytest.fixture(scope="module")
async def redis_client(config):
    """建立並返回一個真實的 Redis 客戶端連線"""
    client = aioredis.from_url(
        config.redis.url,
        encoding="utf-8",
        decode_responses=True
    )
    # 測試連線
    await client.ping()
    yield client
    await client.close()


@pytest.fixture(scope="module")
def workflow(config, redis_client):
    """建立一個使用真實依賴的 SREWorkflow 實例"""
    # 注意：這裡會實例化 SREWorkflow，進而實例化所有真實的工具
    return SREWorkflow(config, redis_client)


@pytest.mark.asyncio
async def test_diagnose_deployment_e2e_integration(workflow, redis_client):
    """
    端到端整合測試，模擬一次完整的部署診斷請求。

    此測試會實際呼叫本地運行的 Prometheus, Loki, 和 Control-Plane 服務。
    """
    session_id = uuid.uuid4()
    # 使用一個在本地環境中可能存在的服務名稱
    # 根據 `docker-compose.yaml` 或本地設定，這可能需要調整
    service_name = "sre-assistant"
    namespace = "default"

    request = DiagnosticRequest(
        incident_id=f"integration-test-{uuid.uuid4()}",
        severity="P3",
        affected_services=[service_name],
        context={
            "namespace": namespace,
            "service_name": service_name
        }
    )

    # 1. 準備：在 Redis 中建立初始任務狀態
    initial_status = DiagnosticStatus(
        session_id=session_id,
        status="processing",
        progress=10,
        current_step="Starting diagnosis..."
    )
    await redis_client.set(
        f"task:{session_id}",
        initial_status.model_dump_json(),
        ex=300  # 5 分鐘後過期
    )

    # 2. 執行：觸發工作流程
    # 在一個真實的應用中，這會由 API 層的背景任務觸發
    await workflow.execute(session_id, request, "deployment")

    # 3. 驗證：從 Redis 中獲取最終結果
    final_status_json = await redis_client.get(f"task:{session_id}")

    assert final_status_json is not None, "任務執行後，Redis 中應存在最終狀態"

    final_status = DiagnosticStatus.model_validate_json(final_status_json)

    # 驗證工作流程是否成功完成
    assert final_status.status == "completed", \
        f"工作流程應成功完成，但狀態為 {final_status.status}，錯誤：{final_status.error}"

    assert final_status.progress == 100, "進度應為 100"

    # 驗證結果是否包含預期的結構
    result = final_status.result
    assert result is not None, "結果不應為空"

    assert "SREWorkflow" in result.summary, "摘要應包含 'SREWorkflow' 字樣"

    # 驗證是否至少有一個調查發現
    assert len(result.findings) > 0, "應至少產生一個調查發現"

    # 驗證調查發現的結構
    for finding in result.findings:
        assert finding.source in ["Prometheus", "Loki", "Control-Plane"], \
            f"未知的調查發現來源: {finding.source}"
        assert finding.message is not None
        assert finding.severity in ["info", "warning", "critical"]

    # 驗證使用的工具列表是否合理
    assert len(result.tools_used) > 0, "應記錄使用的工具"
    assert any("PrometheusQueryTool" in tool for tool in result.tools_used)
    assert any("LokiLogQueryTool" in tool for tool in result.tools_used)
    assert any("ControlPlaneTool" in tool for tool in result.tools_used)

    print("\n--- 整合測試成功 ---")
    print(f"診斷摘要: {result.summary}")
    print(f"調查發現數量: {len(result.findings)}")
    print(f"使用的工具: {result.tools_used}")
    print("--------------------")
