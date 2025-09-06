# services/sre-assistant/src/sre_assistant/main.py
"""
SRE Assistant 主程式入口
提供 REST API 端點供 Control Plane 呼叫 (已重構為非同步)
"""

from fastapi import FastAPI, HTTPException, Depends, Request, BackgroundTasks, Response
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import os
import logging
import uuid
from typing import Dict, Any, Optional

from .contracts import (
    DiagnosticRequest,
    DiagnosticResponse,
    DiagnosticStatus,
)
from .workflow import SREWorkflow
from .config.config_manager import ConfigManager

# 設定日誌
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 全域變數
config_manager: Optional[ConfigManager] = None
workflow: Optional[SREWorkflow] = None
# 注意: 在生產環境中，應使用 Redis 或資料庫來儲存任務狀態
tasks: Dict[uuid.UUID, DiagnosticStatus] = {} # In-memory store for task status
app_ready = False

@asynccontextmanager
async def lifespan(app: FastAPI):
    """應用程式生命週期管理"""
    global config_manager, workflow, tasks, app_ready
    
    logger.info("🚀 正在啟動 SRE Assistant...")
    
    try:
        config_manager = ConfigManager()
        config = config_manager.get_config()

        workflow = SREWorkflow(config)
        tasks = {}
        app_ready = True
        logger.info("✅ 工作流程引擎與任務儲存已初始化")

        logger.info("✅ SRE Assistant 啟動完成")
        yield
    except Exception as e:
        logger.error(f"💀 SRE Assistant 啟動失敗: {e}", exc_info=True)
        app_ready = False
        yield # Still yield to allow the app to run and report not ready
    finally:
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

security = HTTPBearer()

async def verify_token(creds: HTTPAuthorizationCredentials = Depends(security)) -> Dict[str, Any]:
    # 為簡化，我們假設它能正常運作
    return {"sub": "service-account-control-plane"}


# === 背景任務執行器 ===
async def run_workflow_bg(session_id: uuid.UUID, request: DiagnosticRequest):
    """
    一個包裝函式，用於在背景執行工作流程並更新任務狀態。
    """
    global tasks
    tasks[session_id] = DiagnosticStatus(session_id=session_id, status="processing", progress=10, current_step="開始工作流程")
    await workflow.execute(session_id, request, tasks)


# === API 端點 ===

@app.get("/healthz", tags=["Health"])
def check_liveness():
    return {"status": "ok"}

@app.get("/readyz", tags=["Health"])
def check_readiness(response: Response):
    if app_ready and workflow is not None:
        return {"status": "ready"}
    else:
        response.status_code = 503
        return {"status": "not_ready", "reason": "Workflow engine not initialized"}

@app.post("/api/v1/diagnostics/deployment", tags=["Diagnostics"], status_code=202)
async def diagnose_deployment(
    request: DiagnosticRequest,
    background_tasks: BackgroundTasks,
    token: Dict[str, Any] = Depends(verify_token)
) -> DiagnosticResponse:
    """
    接收部署診斷請求，並非同步處理。
    """
    session_id = uuid.uuid4()
    background_tasks.add_task(run_workflow_bg, session_id, request)
    
    return DiagnosticResponse(
        session_id=session_id,
        status="accepted",
        message="診斷任務已接受，正在背景處理中。",
        estimated_time=120
    )

@app.get("/api/v1/diagnostics/{session_id}/status", tags=["Diagnostics"])
async def get_diagnostic_status(
    session_id: uuid.UUID,
    token: Dict[str, Any] = Depends(verify_token)
) -> DiagnosticStatus:
    """
    查詢非同步診斷任務的狀態。
    """
    task = tasks.get(session_id)
    if not task:
        raise HTTPException(status_code=404, detail="找不到指定的診斷任務")
    return task

# --- 待辦：根據 sre-assistant-openapi.yaml 實現其他端點 ---
# @app.post("/api/v1/diagnostics/alerts", ...)
# @app.post("/api/v1/capacity/analyze", ...)
# @app.post("/api/v1/execute", ...)