# services/sre-assistant/src/sre_assistant/main.py
"""
SRE Assistant 主程式入口
提供 REST API 端點供 Control Plane 呼叫 (已重構為非同步)
"""

from fastapi import FastAPI, HTTPException, Depends, Request, BackgroundTasks, Response
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from datetime import datetime, timezone, timedelta
import os
import logging
import uuid
from typing import Dict, Any, Optional, List
import redis.asyncio as redis
from jose import jwt, jwk
from jose.exceptions import JOSEError
import httpx
import time

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
from .config.config_manager import ConfigManager

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
config_manager: Optional[ConfigManager] = None
workflow: Optional[SREWorkflow] = None
redis_client: Optional[redis.Redis] = None
app_ready = False

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    應用程式生命週期管理 (Application Lifespan Management)。

    這個異步上下文管理器會在 FastAPI 應用啟動時執行 `try` 區塊中的程式碼，
    並在應用關閉時執行 `finally` 區塊中的程式碼。
    這對於初始化和清理資源 (如資料庫連接、背景任務) 非常有用。
    """
    global config_manager, workflow, redis_client, app_ready
    
    logger.info("🚀 正在啟動 SRE Assistant...")
    
    try:
        config_manager = ConfigManager()
        config = config_manager.get_config()

        # 初始化 Redis Client
        redis_client = redis.from_url(
            config.redis.url,
            encoding="utf-8",
            decode_responses=True
        )
        await redis_client.ping()
        logger.info("✅ 已成功連接到 Redis")

        # 初始化工作流程引擎，並傳入 Redis client
        workflow = SREWorkflow(config, redis_client)

        app_ready = True
        logger.info("✅ 工作流程引擎與任務儲存已初始化")

        logger.info("✅ SRE Assistant 啟動完成")
        yield
    except Exception as e:
        logger.error(f"💀 SRE Assistant 啟動失敗: {e}", exc_info=True)
        app_ready = False
        yield # Still yield to allow the app to run and report not ready
    finally:
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

security = HTTPBearer()

# --- JWT 驗證邏輯 ---

# JWKS (JSON Web Key Set) 的記憶體快取。
# 為了避免每次驗證 token 都需要向 Keycloak 請求公鑰，我們將公鑰集快取在記憶體中。
# ttl (Time-To-Live) 設定為一小時，過期後會重新獲取。
jwks_cache = {
    "keys": None,
    "last_updated": 0,
    "ttl": 3600
}

async def fetch_jwks(jwks_url: str) -> List[Dict[str, Any]]:
    """
    從 Keycloak 的 JWKS 端點獲取公鑰集。

    實現了簡單的時間快取機制，以降低對 Keycloak 的請求頻率。

    Args:
        jwks_url: Keycloak 的 JWKS 端點 URL。

    Returns:
        一個包含多個公鑰的列表。
    """
    now = time.time()
    if jwks_cache["keys"] and (now - jwks_cache["last_updated"] < jwks_cache["ttl"]):
        return jwks_cache["keys"]

    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(jwks_url)
            response.raise_for_status()
            jwks = response.json()
            jwks_cache["keys"] = jwks.get("keys", [])
            jwks_cache["last_updated"] = now
            logger.info("✅ 成功獲取並快取 JWKS")
            return jwks_cache["keys"]
        except httpx.HTTPStatusError as e:
            logger.error(f"從 Keycloak 獲取 JWKS 失敗: {e}")
            raise HTTPException(status_code=500, detail="無法獲取認證金鑰")
        except Exception as e:
            logger.error(f"處理 JWKS 時發生未知錯誤: {e}")
            raise HTTPException(status_code=500, detail="認證服務內部錯誤")


async def verify_token(creds: HTTPAuthorizationCredentials = Depends(security)) -> Dict[str, Any]:
    """
    驗證來自 Control Plane 的 M2M JWT Token。

    這是一個 FastAPI 的依賴項 (Dependency)，會被注入到需要保護的 API 端點中。
    它會執行以下步驟：
    1. 檢查設定檔，如果 auth provider 不是 keycloak，則跳過驗證。
    2. 從 HTTP Authorization 標頭中提取 Bearer Token。
    3. 獲取 Keycloak 的 JWKS 公鑰集。
    4. 從 Token 的標頭中解析出 `kid` (Key ID)。
    5. 在 JWKS 中尋找與 `kid` 匹配的公鑰。
    6. 使用公鑰驗證 Token 的簽名、發行者 (issuer)、受眾 (audience) 和過期時間。
    7. 如果驗證成功，返回解碼後的 Token payload；否則，拋出 HTTPException。
    """
    config = config_manager.get_config()
    logger.info(f"[DEBUG] In verify_token, auth provider is: '{config.auth.provider}'")
    if config.auth.provider != "keycloak":
        logger.warning("Auth provider 不是 keycloak，跳過 JWT 驗證")
        return {"sub": "service-account-control-plane"}

    logger.info("✅ Keycloak 認證服務已初始化 (Python)")
    token = creds.credentials
    try:
        keycloak_url = config.auth.keycloak.url
        realm = config.auth.keycloak.realm
        audience = config.auth.keycloak.audience

        jwks_url = f"{keycloak_url}/realms/{realm}/protocol/openid-connect/certs"

        jwks_keys = await fetch_jwks(jwks_url)
        if not jwks_keys:
            raise HTTPException(status_code=503, detail="無法加載認證服務公鑰")

        unverified_header = jwt.get_unverified_header(token)
        kid = unverified_header.get("kid")
        if not kid:
            raise HTTPException(status_code=401, detail="Token 標頭中缺少 'kid'")

        rsa_key = {}
        for key in jwks_keys:
            if key["kid"] == kid:
                rsa_key = {
                    "kty": key["kty"],
                    "kid": key["kid"],
                    "use": key["use"],
                    "n": key["n"],
                    "e": key.get("e"), # 'e' is optional for some key types
                }
                break

        if not rsa_key:
            raise HTTPException(status_code=401, detail="找不到對應的公鑰")

        public_key = jwk.construct(rsa_key)

        payload = jwt.decode(
            token,
            public_key,
            algorithms=["RS256"],
            audience=audience,
            issuer=f"{keycloak_url}/realms/{realm}"
        )
        return payload

    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token 已過期")
    except jwt.JWTClaimsError as e:
        raise HTTPException(status_code=401, detail=f"Token claims 錯誤: {e}")
    except JOSEError as e:
        logger.error(f"JWT 解碼/驗證錯誤: {e}", exc_info=True)
        raise HTTPException(status_code=401, detail=f"無效的 Token: {e}")
    except Exception as e:
        logger.error(f"未知的 Token 驗證錯誤: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Token 驗證時發生內部錯誤")


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
    import time

    # 計算運行時間（從應用啟動至今）
    uptime = int(time.time() - startup_time) if 'startup_time' in globals() else 0

    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "version": "1.0.0",
        "uptime": uptime
    }

from prometheus_client import generate_latest, CONTENT_TYPE_LATEST

@app.get("/api/v1/readyz", tags=["Health"])
async def check_readiness(response: Response):
    """
    執行深入的就緒檢查，驗證所有後端依賴是否可用。
    """
    checks = {
        "redis": False,
        "prometheus": False,
        "loki": False,
        "control_plane": False
    }

    if not app_ready or not workflow or not redis_client:
        response.status_code = 503
        return {
            "ready": False,
            "checks": checks
        }

    try:
        # 驗證與 Redis 的即時連線
        await redis_client.ping()
        checks["redis"] = True

        # 這裡可以加入其他依賴檢查
        # TODO: 檢查與 Prometheus 的連線
        # TODO: 檢查與 Loki 的連線
        # TODO: 檢查與 Control Plane 的連線

        # 目前只檢查 Redis，所以其他檢查設為 True（表示不進行檢查）
        checks["prometheus"] = True
        checks["loki"] = True
        checks["control_plane"] = True

        return {
            "ready": all(checks.values()),
            "checks": checks
        }
    except redis.exceptions.ConnectionError as e:
        logger.error(f"Redis 連線檢查失敗: {e}", exc_info=True)
        response.status_code = 503
        return {
            "ready": False,
            "checks": checks
        }
    except Exception as e:
        logger.error(f"就緒檢查時發生未預期的錯誤: {e}", exc_info=True)
        response.status_code = 503
        return {
            "ready": False,
            "checks": checks
        }

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
    # 這是同步端點的骨架，目前返回模擬數據
    # 實際邏輯將在 workflow.py 中實現
    logger.info(f"接收到容量分析請求: {request.resource_ids}")
    # TODO: 呼叫 workflow 中的同步方法
    return CapacityAnalysisResponse(
        current_usage={"average": 55.5, "peak": 80.2},
        forecast={"trend": "increasing", "days_to_capacity": 45},
        recommendations=[{"type": "scale_up", "resource": request.resource_ids[0], "priority": "high", "reasoning": "預測使用量將在 45 天後達到瓶頸"}]
    )

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