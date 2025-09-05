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
    # AlertAnalysisRequest, # Placeholder for when you implement it
    # CapacityAnalysisRequest, # Placeholder
    # ExecuteRequest, # Placeholder
)
from .workflow import SREWorkflow
from .config.config_manager import ConfigManager

# 設定日誌
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 全域變數
config_manager: Optional[ConfigManager] = None
jwks_client: Optional[PyJWKClient] = None
workflow: Optional[SREWorkflow] = None
# 注意: 在生產環境中，應使用 Redis 或資料庫來儲存任務狀態
tasks: Dict[uuid.UUID, DiagnosticStatus] = {} # In-memory store for task status

@asynccontextmanager
async def lifespan(app: FastAPI):
    """應用程式生命週期管理"""
    global config_manager, jwks_client, workflow, tasks
    
    logger.info("🚀 正在啟動 SRE Assistant...")
    
    config_manager = ConfigManager()
    config = config_manager.get_config()
    
    # 這裡的認證邏輯保持不變
    # ...

    workflow = SREWorkflow(config)
    tasks = {}
    logger.info("✅ 工作流程引擎與任務儲存已初始化")
    
    logger.info("✅ SRE Assistant 啟動完成")
    yield
    
    logger.info("🛑 正在關閉 SRE Assistant...")

app = FastAPI(
    title="SRE Platform API",
    version="1.0.0",
    description="SRE Platform 的非同步診斷與分析引擎",
    lifespan=lifespan
)

# CORS 中介軟體保持不變
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

security = HTTPBearer()

async def verify_token(creds: HTTPAuthorizationCredentials = Depends(security)) -> Dict[str, Any]:
    # 實際的 JWT 驗證邏輯...
    # 為簡化，我們假設它能正常運作
    return {"sub": "service-account-control-plane"}


# === 背景任務執行器 ===
async def run_workflow_bg(session_id: uuid.UUID, request: DiagnosticRequest):
    """
    一個包裝函式，用於在背景執行工作流程並更新任務狀態。
    """
    global tasks
    # 初始狀態
    tasks[session_id] = DiagnosticStatus(session_id=session_id, status="processing", progress=10, current_step="開始工作流程")
    await workflow.execute(session_id, request, tasks)


# === API 端點 ===

@app.get("/healthz", tags=["Health"])
def check_liveness():
    return {"status": "ok"}

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
    
    # 將耗時的 `workflow.execute` 任務添加到背景執行
    background_tasks.add_task(run_workflow_bg, session_id, request)
    
    # 立即返回，告知客戶端任務已接受
    return DiagnosticResponse(
        session_id=session_id,
        status="accepted",
        message="診斷任務已接受，正在背景處理中。",
        estimated_time=120 # 預估 120 秒
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

# --- 待辦：根據 openapi.yaml 實現其他端點 ---
# @app.post("/api/v1/diagnostics/alerts", ...)
# @app.post("/api/v1/capacity/analyze", ...)
# @app.post("/api/v1/execute", ...)