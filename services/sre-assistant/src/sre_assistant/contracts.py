# services/sre-assistant/src/sre_assistant/contracts.py
# 更新版本：加入 API 端點所需的所有資料模型

from pydantic import BaseModel, Field, field_validator, ValidationInfo
from typing import Dict, List, Optional, Union, Literal, Any
from datetime import datetime
from enum import Enum

# === 既有的 Enum 和基礎模型 ===

class SeverityLevel(str, Enum):
    """事件嚴重程度等級"""
    P0 = "P0"  # 關鍵事件
    P1 = "P1"  # 高優先級
    P2 = "P2"  # 中優先級
    P3 = "P3"  # 低優先級

class RiskLevel(str, Enum):
    """操作風險等級"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"

class AuthProvider(str, Enum):
    """認證提供者選項"""
    NONE = "none"
    GOOGLE_IAM = "google_iam"
    OAUTH2 = "oauth2"
    API_KEY = "api_key"
    JWT = "jwt"
    MTLS = "mtls"
    LOCAL = "local"

# === API 請求模型 ===

class DeploymentDiagnosticRequest(BaseModel):
    """部署診斷請求"""
    deployment_id: str = Field(..., description="部署的唯一標識符")
    service_name: str = Field(..., description="服務名稱")
    namespace: str = Field(default="default", description="Kubernetes 命名空間")
    image_tag: Optional[str] = Field(None, description="部署的映像標籤")
    
class AlertDiagnosticRequest(BaseModel):
    """告警診斷請求"""
    incident_ids: List[int] = Field(..., description="告警事件 ID 列表")
    service_name: Optional[str] = Field(None, description="相關服務名稱")
    time_range: Optional[Dict[str, str]] = Field(None, description="分析時間範圍")

class CapacityAnalysisRequest(BaseModel):
    """容量分析請求"""
    resource_group: str = Field(..., description="資源群組名稱")
    metric: str = Field(..., description="要分析的指標")
    prediction_days: int = Field(default=30, description="預測天數")

# === API 回應模型 ===

class Finding(BaseModel):
    """診斷發現項目"""
    source: str = Field(..., description="資料來源 (Prometheus/Loki/Control-Plane)")
    severity: Optional[SeverityLevel] = Field(None, description="發現的嚴重程度")
    data: Dict[str, Any] = Field(..., description="具體的發現數據")
    timestamp: Optional[datetime] = Field(None, description="發現時間")

class SREResponse(BaseModel):
    """標準化 SRE 回應模型"""
    status: Literal["COMPLETED", "FAILED", "PARTIAL"] = Field(..., description="執行狀態")
    summary: str = Field(..., description="診斷或分析摘要")
    findings: List[Finding] = Field(default_factory=list, description="詳細發現列表")
    recommended_action: Optional[str] = Field(None, description="建議的修復動作")
    confidence_score: float = Field(default=0.0, ge=0.0, le=1.0, description="結果信心分數")
    execution_time_ms: Optional[int] = Field(None, description="執行時間（毫秒）")
    
# === 工具相關模型 ===

class ToolError(BaseModel):
    """標準化的工具錯誤模型"""
    code: str = Field(..., description="錯誤代碼")
    message: str = Field(..., description="錯誤訊息")
    details: Optional[Dict[str, Any]] = Field(None, description="額外錯誤詳情")

class ToolResult(BaseModel):
    """標準化的工具返回結果"""
    success: bool = Field(..., description="執行是否成功")
    data: Optional[Dict[str, Any]] = Field(None, description="返回的數據")
    error: Optional[ToolError] = Field(None, description="錯誤資訊")
    metadata: Optional[Dict[str, Any]] = Field(None, description="執行元數據")

# === 內部使用模型 ===

class SRERequest(BaseModel):
    """內部標準化 SRE 請求模型"""
    incident_id: str = Field(..., description="事件的唯一標識符")
    severity: SeverityLevel = Field(..., description="事件嚴重程度")
    input: str = Field(..., min_length=1, description="原始輸入或告警內容")
    affected_services: List[str] = Field(default_factory=list)
    context: Dict[str, Any] = Field(default_factory=dict)
    session_id: Optional[str] = Field(None)
    trace_id: Optional[str] = Field(None)

class AuthConfig(BaseModel):
    """認證配置模型"""
    provider: AuthProvider = AuthProvider.NONE
    service_account_path: Optional[str] = None
    impersonate_service_account: Optional[str] = None
    oauth_client_id: Optional[str] = None
    oauth_client_secret: Optional[str] = None
    oauth_redirect_uri: Optional[str] = None
    oauth_scopes: List[str] = Field(default_factory=list)
    jwt_secret: Optional[str] = None
    jwt_algorithm: str = "HS256"
    jwt_expiry_seconds: int = 3600
    jwks_url: Optional[str] = None  # 新增：JWKS URL
    api_key_header: str = "X-API-Key"
    api_keys_file: Optional[str] = None
    mtls_cert_path: Optional[str] = None
    mtls_key_path: Optional[str] = None
    mtls_ca_path: Optional[str] = None
    enable_rbac: bool = True
    enable_rate_limiting: bool = True
    max_requests_per_minute: int = 60
    enable_audit_logging: bool = True

    @field_validator('service_account_path', mode='before')
    @classmethod
    def validate_google_iam(cls, v: str, info: ValidationInfo) -> str:
        if info.data.get('provider') == AuthProvider.GOOGLE_IAM and not v:
            raise ValueError("service_account_path is required for Google IAM provider")
        return v

# === 工作流程相關模型 ===

class WorkflowStep(BaseModel):
    """工作流程步驟"""
    name: str = Field(..., description="步驟名稱")
    tool: str = Field(..., description="使用的工具")
    params: Dict[str, Any] = Field(default_factory=dict, description="工具參數")
    timeout_seconds: int = Field(default=30, description="超時時間")
    retry_count: int = Field(default=1, description="重試次數")

class WorkflowDefinition(BaseModel):
    """工作流程定義"""
    name: str = Field(..., description="工作流程名稱")
    steps: List[WorkflowStep] = Field(..., description="步驟列表")
    parallel: bool = Field(default=False, description="是否並行執行")
    on_failure: Optional[str] = Field(None, description="失敗時的處理策略")