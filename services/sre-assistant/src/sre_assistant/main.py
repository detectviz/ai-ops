# services/sre-assistant/src/sre_assistant/main.py
"""
SRE Assistant 主程式入口
提供 REST API 端點供 Control Plane 呼叫 (已重構為非同步)
"""

from fastapi import FastAPI, HTTPException, Depends, Request, BackgroundTasks, Response
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from datetime import datetime, timezone, timedelta
import uuid
import asyncio
from typing import Dict, Any, Optional, List
import redis.asyncio as redis
import asyncpg
import time
import httpx
from prometheus_client import generate_latest, CONTENT_TYPE_LATEST

# 依賴項和認證邏輯已重構
from .dependencies import config_manager
from .auth import verify_token

from .contracts import (
    DiagnosticRequest,
    DiagnosticResponse,
    DiagnosticStatus,
    AlertAnalysisRequest,
    CapacityAnalysisRequest,
    CapacityAnalysisResponse,
    ExecuteRequest,
    DiagnosticHistoryList,
    DiagnosticHistoryItem,
    WorkflowTemplate,
    ToolStatus,
    Pagination,
)
from .workflow import SREWorkflow, SREWorkflowRequest

# --- 結構化日誌設定 ---
import structlog
import contextvars

# 1. 為請求 ID 建立 ContextVar
request_id_var = contextvars.ContextVar("request_id", default=None)

def configure_logging():
    """設定 structlog 以輸出 JSON 格式的日誌"""

    # structlog 處理器鏈
    processors = [
        # 將 contextvars (如 request_id) 合併到日誌記錄中
        structlog.contextvars.merge_contextvars,
        # 新增日誌級別和名稱等標準屬性
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        # 新增時間戳
        structlog.processors.TimeStamper(fmt="iso"),
        # 如果有異常，格式化它
        structlog.processors.format_exc_info,
        # 渲染為 JSON
        structlog.processors.JSONRenderer(),
    ]

    structlog.configure(
        processors=processors,
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )

# 在應用啟動時設定日誌
configure_logging()
logger = structlog.get_logger(__name__)
# --- 結構化日誌設定結束 ---

# 全域變數
workflow: Optional[SREWorkflow] = None
redis_client: Optional[redis.Redis] = None
db_pool: Optional[asyncpg.Pool] = None
http_client: Optional[httpx.AsyncClient] = None
app_ready = False
startup_time = time.time() # 應用程式啟動時間

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    應用程式生命週期管理 (Application Lifespan Management)。

    這個異步上下文管理器會在 FastAPI 應用啟動時執行 `try` 區塊中的程式碼，
    並在應用關閉時執行 `finally` 區塊中的程式碼。
    這對於初始化和清理資源 (如資料庫連接、背景任務) 非常有用。
    """
    global workflow, redis_client, db_pool, http_client, app_ready
    
    logger.info("🚀 正在啟動 SRE Assistant...")
    
    try:
        config = config_manager.get_config()

        # 初始化 Redis Client
        redis_client = redis.from_url(
            config.redis.url,
            encoding="utf-8",
            decode_responses=True
        )
        await redis_client.ping()
        logger.info("✅ 已成功連接到 Redis")

        # 僅在非測試環境中初始化 PostgreSQL 連線池
        if config.get("environment") != "test":
            db_pool = await asyncpg.create_pool(
                dsn=config.database.url,
                min_size=5,
                max_size=20
            )
            # 嘗試獲取一個連線以驗證連線能力
            async with db_pool.acquire():
                logger.info("✅ 已成功連接到 PostgreSQL")
        else:
            logger.info("📝 偵測到測試環境，跳過 PostgreSQL 連線池初始化。")

        # 建立一個共享的、具有重試功能的 HTTP 客戶端
        # 設定重試策略：針對 5xx 錯誤和連線錯誤，最多重試 3 次
        transport = httpx.AsyncHTTPTransport(retries=3)
        # 設定連線池限制
        limits = httpx.Limits(max_connections=100, max_keepalive_connections=20)
        http_client = httpx.AsyncClient(transport=transport, limits=limits, http2=True)
        logger.info("✅ 共享的 HTTP 客戶端已建立，並設定了重試與連線池")

        # 初始化工作流程引擎，並傳入共享的客戶端
        workflow = SREWorkflow(config, redis_client, http_client)

        app_ready = True
        logger.info("✅ 工作流程引擎與任務儲存已初始化")

        logger.info("✅ SRE Assistant 啟動完成")
        yield
    except Exception as e:
        logger.error(f"💀 SRE Assistant 啟動失敗: {e}", exc_info=True)
        app_ready = False
        yield # Still yield to allow the app to run and report not ready
    finally:
        # 在應用程式關閉時，優雅地關閉所有客戶端和連線池
        if http_client:
            await http_client.aclose()
            logger.info("HTTP 客戶端已關閉")
        if db_pool:
            await db_pool.close()
            logger.info("PostgreSQL 連線池已關閉")
        if redis_client:
            await redis_client.close()
            logger.info("Redis 連線已關閉")
        logger.info("🛑 正在關閉 SRE Assistant...")
        app_ready = False


app = FastAPI(
    title="SRE Platform API",
    version="1.0.0",
    description="SRE Platform 的非同步診斷與分析引擎",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Request ID 中介層 ---
@app.middleware("http")
async def request_id_middleware(request: Request, call_next):
    """
    攔截請求，生成唯一的 request_id，並將其放入 context var。
    """
    request_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))
    request_id_var.set(request_id)
    response = await call_next(request)
    response.headers["X-Request-ID"] = request_id
    return response

# 認證邏輯已重構至 auth.py


# === 背景任務執行器 ===
async def run_workflow_bg(session_id: uuid.UUID, request: SREWorkflowRequest, request_type: str):
    """
    一個通用的包裝函式，用於在背景執行工作流程並更新任務狀態。

    Args:
        session_id: 此次任務的唯一會話 ID。
        request: API 請求的資料模型。
        request_type: 請求的類型，用於在工作流程中進行路由。
    """
    initial_status = DiagnosticStatus(
        session_id=session_id,
        status="processing",
        progress=10,
        current_step=f"開始執行 {request_type} 工作流程"
    )
    # 將初始狀態寫入 Redis，設定 24 小時過期
    await redis_client.set(
        str(session_id),
        initial_status.model_dump_json(),
        ex=86400
    )
    await workflow.execute(session_id, request, request_type)


# === API 端點 ===

@app.get("/api/v1/healthz", tags=["Health"])
def check_liveness():
    """
    健康檢查端點 - 驗證服務是否正常運行
    返回 HealthStatus 結構，符合 OpenAPI 規範
    """
    from datetime import datetime

    # 計算運行時間（從應用啟動至今）
    uptime = int(time.time() - startup_time)

    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "version": "1.0.0",
        "uptime": uptime
    }

@app.get("/api/v1/readyz", tags=["Health"])
async def check_readiness(response: Response):
    """
    執行深入的就緒檢查，驗證所有後端依賴是否可用。
    """
    checks = {
        "redis": False,
        "database": False,
        "prometheus": False,
        "loki": False,
        "control_plane": False
    }

    if not app_ready or not workflow or not redis_client:
        response.status_code = 503
        return {"ready": False, "checks": checks}

    async def check_db_health():
        """一個簡短的輔助函式，用於檢查資料庫連線。"""
        if not db_pool:
            return True # 在測試環境中，db_pool 為 None
        try:
            async with db_pool.acquire() as connection:
                await connection.fetchval("SELECT 1")
            return True
        except Exception as e:
            logger.error(f"資料庫健康檢查失敗: {e}")
            return False

    try:
        # 使用 asyncio.gather 並行執行所有健康檢查
        results = await asyncio.gather(
            redis_client.ping(),
            check_db_health(),
            workflow.prometheus_tool.check_health(),
            workflow.loki_tool.check_health(),
            workflow.control_plane_tool.check_health(),
            return_exceptions=True  # 即使有檢查失敗也繼續
        )

        # 處理檢查結果
        checks["redis"] = results[0] is True
        checks["database"] = results[1] is True
        checks["prometheus"] = results[2] is True
        checks["loki"] = results[3] is True
        checks["control_plane"] = results[4] is True

        is_ready = all(checks.values())
        if not is_ready:
            response.status_code = 503

        return {"ready": is_ready, "checks": checks}
    except Exception as e:
        # 這是最後的防線，捕捉 asyncio.gather 本身或其他未預期的錯誤
        logger.error(f"就緒檢查時發生未預期的錯誤: {e}", exc_info=True)
        response.status_code = 503
        return {"ready": False, "checks": checks}

@app.get("/api/v1/metrics", tags=["Health"])
def get_metrics():
    """提供 Prometheus 格式的指標"""
    return Response(content=generate_latest(), media_type=CONTENT_TYPE_LATEST)

@app.post("/api/v1/diagnostics/deployment", tags=["Diagnostics"], status_code=202, response_model=DiagnosticResponse)
async def diagnose_deployment(
    request: DiagnosticRequest,
    background_tasks: BackgroundTasks,
    token: Dict[str, Any] = Depends(verify_token)
):
    """
    接收部署診斷請求，並非同步處理。
    """
    session_id = uuid.uuid4()
    background_tasks.add_task(run_workflow_bg, session_id, request, "deployment")
    
    return DiagnosticResponse(
        session_id=session_id,
        status="accepted",
        message="部署診斷任務已接受，正在背景處理中。",
        estimated_time=120
    )

@app.get("/api/v1/diagnostics/{sessionId}/status", tags=["Diagnostics"], response_model=DiagnosticStatus)
async def get_diagnostic_status(
    sessionId: uuid.UUID,
    token: Dict[str, Any] = Depends(verify_token)
):
    """
    查詢非同步診斷任務的狀態。
    """
    task_json = await redis_client.get(str(sessionId))
    if not task_json:
        raise HTTPException(status_code=404, detail="找不到指定的診斷任務")

    return DiagnosticStatus.model_validate_json(task_json)

# --- New Endpoints ---

@app.post("/api/v1/diagnostics/alerts", tags=["Diagnostics"], status_code=202, response_model=DiagnosticResponse)
async def analyze_alerts(
    request: AlertAnalysisRequest,
    background_tasks: BackgroundTasks,
    token: Dict[str, Any] = Depends(verify_token)
):
    """
    接收告警分析請求，並非同步處理。
    """
    session_id = uuid.uuid4()
    background_tasks.add_task(run_workflow_bg, session_id, request, "alert_analysis")

    return DiagnosticResponse(
        session_id=session_id,
        status="accepted",
        message="告警分析任務已接受，正在背景處理中。",
        estimated_time=60
    )

@app.post("/api/v1/diagnostics/capacity", tags=["Diagnostics"], status_code=200, response_model=CapacityAnalysisResponse)
async def analyze_capacity(
    request: CapacityAnalysisRequest,
    token: Dict[str, Any] = Depends(verify_token)
):
    """
    接收容量分析請求，並同步處理。
    """
    if not workflow:
        raise HTTPException(status_code=503, detail="工作流程引擎尚未初始化。")

    # 呼叫工作流程中新的、具備真實邏輯的方法
    return await workflow.analyze_capacity(request)

@app.post("/api/v1/execute", tags=["Diagnostics"], status_code=202, response_model=DiagnosticResponse)
async def execute_query(
    request: ExecuteRequest,
    background_tasks: BackgroundTasks,
    token: Dict[str, Any] = Depends(verify_token)
):
    """
    接收自然語言查詢請求，並非同步處理。
    """
    session_id = uuid.uuid4()
    background_tasks.add_task(run_workflow_bg, session_id, request, "execute_query")

    return DiagnosticResponse(
        session_id=session_id,
        status="accepted",
        message="自然語言查詢任務已接受，正在背景處理中。",
        estimated_time=180
    )

@app.get("/api/v1/diagnostics/history", tags=["Diagnostics"], response_model=DiagnosticHistoryList)
async def get_diagnostic_history(
    page: int = 1,
    page_size: int = 20,
    token: Dict[str, Any] = Depends(verify_token)
):
    """
    查詢歷史診斷記錄 (骨架)。
    """
    # 模擬數據
    items = [
        DiagnosticHistoryItem(
            session_id=uuid.uuid4(),
            incident_id="INC-2025-001",
            status="completed",
            created_at=datetime.now(timezone.utc) - timedelta(hours=1),
            completed_at=datetime.now(timezone.utc) - timedelta(minutes=50),
            summary="初步診斷未發現明顯問題。"
        )
    ]
    return DiagnosticHistoryList(
        items=items,
        pagination=Pagination(page=page, page_size=page_size, total=len(items), total_pages=1)
    )

@app.get("/api/v1/workflows/templates", tags=["Workflows"], response_model=List[WorkflowTemplate])
async def list_workflow_templates(token: Dict[str, Any] = Depends(verify_token)):
    """
    獲取工作流模板 (骨架)。
    """
    # 模擬數據
    templates = [
        WorkflowTemplate(id="deployment_diagnosis", name="部署問題診斷", description="分析部署失敗或應用程式啟動異常問題。", parameters=[]),
        WorkflowTemplate(id="alert_correlation", name="告警關聯分析", description="分析多個告警之間的關聯性，尋找根本原因。", parameters=[{"name": "alert_ids", "type": "list"}]),
    ]
    return templates

@app.get("/api/v1/tools/status", tags=["Tools"], response_model=Dict[str, ToolStatus])
async def get_tools_status(token: Dict[str, Any] = Depends(verify_token)):
    """
    獲取工具狀態 (骨架)。
    """
    # 模擬數據
    now = datetime.now(timezone.utc)
    return {
        "prometheus": ToolStatus(status="healthy", last_checked=now),
        "loki": ToolStatus(status="healthy", last_checked=now),
        "control_plane": ToolStatus(status="unhealthy", last_checked=now, details={"error": "Connection timeout"})
    }
