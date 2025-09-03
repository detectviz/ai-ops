# services/sre-assistant/src/sre_assistant/main.py
"""
SRE Assistant 主程式入口
提供 REST API 端點供 Control Plane 呼叫
"""

from fastapi import FastAPI, HTTPException, Depends, Security
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import os
import logging
from typing import Dict, Any, Optional
from datetime import datetime, timezone
import httpx
import jwt
from jwt import PyJWKClient

from .contracts import (
    SRERequest,
    SREResponse,
    DeploymentDiagnosticRequest,
    AlertDiagnosticRequest,
    CapacityAnalysisRequest,
    ToolResult
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

@asynccontextmanager
async def lifespan(app: FastAPI):
    """應用程式生命週期管理"""
    global config_manager, jwks_client, workflow
    
    logger.info("🚀 正在啟動 SRE Assistant...")
    
    # 載入配置
    config_manager = ConfigManager()
    config = config_manager.get_config()
    
    # 初始化 JWT 驗證客戶端
    if config.auth.provider == "jwt":
        jwks_url = os.getenv(
            "KEYCLOAK_JWKS_URL",
            config.auth.jwks_url or "http://keycloak:8080/realms/sre-platform/protocol/openid-connect/certs"
        )
        jwks_client = PyJWKClient(jwks_url)
        logger.info(f"✅ JWT 驗證已設定: {jwks_url}")
    
    # 初始化工作流程
    workflow = SREWorkflow(config)
    logger.info("✅ 工作流程引擎已初始化")
    
    logger.info("✅ SRE Assistant 啟動完成")
    yield
    
    # 清理資源
    logger.info("🛑 正在關閉 SRE Assistant...")

# 建立 FastAPI 應用
app = FastAPI(
    title="SRE Assistant API",
    description="無介面的 SRE 專家代理，提供診斷、分析與自動化修復能力",
    version="3.0.0",
    lifespan=lifespan
)

# CORS 中介軟體
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:8081",  # Control Plane
        "http://control-plane:8081",
        "http://localhost:3000",  # Grafana
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 安全性設定
security = HTTPBearer()

async def verify_token(credentials: HTTPAuthorizationCredentials = Security(security)) -> Dict[str, Any]:
    """驗證 JWT Token"""
    token = credentials.credentials
    
    # 開發模式：如果沒有設定 JWKS，跳過驗證
    if not jwks_client:
        logger.warning("⚠️ JWT 驗證已停用 (開發模式)")
        return {"sub": "dev-user", "roles": ["admin"]}
    
    try:
        # 從 JWKS 獲取簽名金鑰
        signing_key = jwks_client.get_signing_key_from_jwt(token)
        
        # 驗證 token
        payload = jwt.decode(
            token,
            signing_key.key,
            algorithms=["RS256"],
            audience=os.getenv("OAUTH_CLIENT_ID", "sre-assistant"),
            options={"verify_exp": True}
        )
        
        logger.info(f"✅ Token 驗證成功: {payload.get('sub')}")
        return payload
        
    except jwt.ExpiredSignatureError:
        logger.error("Token 已過期")
        raise HTTPException(status_code=401, detail="Token 已過期")
    except jwt.InvalidTokenError as e:
        logger.error(f"Token 驗證失敗: {e}")
        raise HTTPException(status_code=401, detail="無效的 Token")

# === API 端點 ===

@app.get("/health")
async def health_check():
    """健康檢查端點"""
    return {
        "status": "healthy",
        "service": "sre-assistant",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "version": "3.0.0",
        "dependencies": {
            "database": await check_database(),
            "redis": await check_redis(),
            "keycloak": await check_keycloak()
        }
    }

@app.get("/ready")
async def readiness_check():
    """就緒檢查端點"""
    checks = {
        "workflow": workflow is not None,
        "config": config_manager is not None,
        "auth": jwks_client is not None or config_manager.get_config().auth.provider != "jwt"
    }
    
    if all(checks.values()):
        return {"status": "ready", "checks": checks}
    else:
        raise HTTPException(status_code=503, detail={"status": "not ready", "checks": checks})

@app.post("/diagnostics/deployment", response_model=SREResponse)
async def diagnose_deployment(
    request: DeploymentDiagnosticRequest,
    token_payload: Dict = Depends(verify_token)
):
    """
    診斷部署健康狀況
    
    當部署失敗或異常時，執行端到端的診斷流程
    """
    logger.info(f"📊 開始診斷部署: {request.service_name} (ID: {request.deployment_id})")
    
    try:
        # 建構 SRE 請求
        sre_request = SRERequest(
            incident_id=f"deploy-diag-{request.deployment_id}",
            severity="P2",
            input=f"診斷部署失敗: {request.service_name}",
            affected_services=[request.service_name],
            context={
                "deployment_id": request.deployment_id,
                "namespace": request.namespace,
                "triggered_by": token_payload.get("sub", "unknown"),
                "type": "deployment_diagnosis"
            }
        )
        
        # 執行工作流程
        result = await workflow.execute(sre_request)
        
        return SREResponse(
            status="COMPLETED",
            summary=result.get("summary", "診斷完成"),
            findings=result.get("findings", []),
            recommended_action=result.get("recommended_action"),
            confidence_score=result.get("confidence_score", 0.8)
        )
        
    except Exception as e:
        logger.error(f"診斷失敗: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/diagnostics/alerts", response_model=SREResponse)
async def diagnose_alerts(
    request: AlertDiagnosticRequest,
    token_payload: Dict = Depends(verify_token)
):
    """
    分析告警事件
    
    將多個告警關聯分析，找出共同模式
    """
    logger.info(f"🚨 開始分析告警: {request.incident_ids}")
    
    try:
        sre_request = SRERequest(
            incident_id=f"alert-diag-{'-'.join(map(str, request.incident_ids))}",
            severity="P1" if len(request.incident_ids) > 5 else "P2",
            input=f"分析告警事件: {request.service_name or 'multiple services'}",
            affected_services=[request.service_name] if request.service_name else [],
            context={
                "incident_ids": request.incident_ids,
                "triggered_by": token_payload.get("sub", "unknown"),
                "type": "alert_diagnosis"
            }
        )
        
        result = await workflow.execute(sre_request)
        
        return SREResponse(
            status="COMPLETED",
            summary=result.get("summary", "告警分析完成"),
            findings=result.get("findings", []),
            recommended_action=result.get("recommended_action"),
            confidence_score=result.get("confidence_score", 0.75)
        )
        
    except Exception as e:
        logger.error(f"告警分析失敗: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/execute", response_model=SREResponse)
async def execute_query(
    request: Dict[str, Any],
    token_payload: Dict = Depends(verify_token)
):
    """
    通用查詢執行端點
    
    處理自然語言查詢和臨機任務
    """
    logger.info(f"💬 執行通用查詢: {request.get('user_query', '')[:100]}")
    
    try:
        sre_request = SRERequest(
            incident_id=f"query-{datetime.now(timezone.utc).timestamp()}",
            severity="P3",
            input=request.get("user_query", ""),
            affected_services=request.get("context", {}).get("services", []),
            context={
                **request.get("context", {}),
                "triggered_by": token_payload.get("sub", "unknown"),
                "type": "ad_hoc_query"
            }
        )
        
        result = await workflow.execute(sre_request)
        
        return SREResponse(
            status="COMPLETED",
            summary=result.get("summary", "查詢完成"),
            findings=result.get("findings", []),
            recommended_action=result.get("recommended_action"),
            confidence_score=result.get("confidence_score", 0.7)
        )
        
    except Exception as e:
        logger.error(f"查詢執行失敗: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# === 輔助函式 ===

async def check_database() -> str:
    """檢查資料庫連線"""
    try:
        # TODO: 實作實際的資料庫檢查
        return "healthy"
    except Exception:
        return "unhealthy"

async def check_redis() -> str:
    """檢查 Redis 連線"""
    try:
        # TODO: 實作實際的 Redis 檢查
        return "healthy"
    except Exception:
        return "unhealthy"

async def check_keycloak() -> str:
    """檢查 Keycloak 連線"""
    try:
        if not jwks_client:
            return "not configured"
        
        # 嘗試連線到 JWKS 端點
        async with httpx.AsyncClient() as client:
            response = await client.get(jwks_client.uri)
            if response.status_code == 200:
                return "healthy"
        return "unhealthy"
    except Exception:
        return "unhealthy"

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "src.sre_assistant.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True
    )