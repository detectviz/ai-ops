# services/sre-assistant/src/sre_assistant/contracts.py
"""
Data models and contracts for the SRE Assistant.
"""
from typing import Dict, List, Optional, Any, Literal
from pydantic import BaseModel, Field
from datetime import datetime
import uuid

# ============================================
# API Request/Response Models
# ============================================

class DiagnosticRequest(BaseModel):
    """定義一個診斷請求的資料結構，通常由 Control Plane 發起。"""
    incident_id: str = Field(..., description="事件 ID")
    severity: Literal['P0', 'P1', 'P2', 'P3'] = Field(..., description="嚴重程度")
    title: Optional[str] = Field(None, description="事件標題")
    description: Optional[str] = Field(None, description="問題描述")
    affected_services: List[str] = Field(..., description="受影響的服務列表")
    time_range: Optional[Dict[str, datetime]] = Field(None, description="時間範圍")
    context: Dict[str, Any] = Field({}, description="額外上下文資訊")

class DiagnosticResponse(BaseModel):
    """代表一個被接受的非同步任務的回應。"""
    session_id: uuid.UUID = Field(..., description="診斷會話 ID")
    status: Literal['accepted'] = Field("accepted", description="狀態")
    message: Optional[str] = Field(None, description="狀態訊息")
    estimated_time: Optional[int] = Field(None, description="預估完成時間（秒）")

class Finding(BaseModel):
    """代表一個由診斷工具產生的具體發現。"""
    source: str = Field(..., description="發現來源（如 Prometheus, Loki）")
    severity: Literal['critical', 'warning', 'info'] = Field(..., description="嚴重程度")
    message: str = Field(..., description="發現描述")
    evidence: Optional[Dict[str, Any]] = Field(None, description="支撐證據")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="時間戳")

class DiagnosticResult(BaseModel):
    """儲存一次完整診斷的最終結果。"""
    summary: Optional[str] = Field(None, description="診斷摘要")
    findings: List[Finding] = Field([], description="發現列表")
    recommended_actions: List[str] = Field([], description="建議採取的行動")
    confidence_score: Optional[float] = Field(None, description="診斷信心分數", ge=0, le=1)
    tools_used: List[str] = Field([], description="使用的診斷工具")
    execution_plan: Optional[List[str]] = Field(None, description="執行的診斷步驟計畫")
    execution_time: Optional[float] = Field(None, description="執行時間（秒）")

class DiagnosticStatus(BaseModel):
    """代表一個非同步診斷任務的當前狀態。"""
    session_id: uuid.UUID = Field(..., description="會話 ID")
    status: Literal['processing', 'completed', 'failed'] = Field(..., description="狀態")
    progress: Optional[int] = Field(None, description="進度百分比", ge=0, le=100)
    current_step: Optional[str] = Field(None, description="當前執行步驟")
    result: Optional[DiagnosticResult] = Field(None, description="診斷結果")
    error: Optional[str] = Field(None, description="錯誤訊息（如果失敗）")


# ============================================
# Internal Workflow Models
# ============================================

class ToolError(BaseModel):
    """定義工具執行失敗時的錯誤結構。"""
    code: str
    message: str
    details: Optional[Dict[str, Any]] = None

class ToolResult(BaseModel):
    """定義單一工具執行的標準回傳格式。"""
    success: bool
    data: Optional[Dict[str, Any]] = None
    error: Optional[ToolError] = None

# ============================================
# New API Contracts from openapi.yaml
# ============================================

class AlertAnalysisRequest(BaseModel):
    """定義告警分析請求的資料結構。"""
    alert_ids: List[str] = Field(..., description="要分析的告警 ID 列表")
    correlation_window: int = Field(300, description="關聯時間窗口（秒）")

class CapacityAnalysisRequest(BaseModel):
    """定義容量分析請求的資料結構。"""
    resource_ids: List[str] = Field(..., description="要分析的資源 ID 列表")
    metric_type: Literal['cpu', 'memory', 'disk', 'network'] = Field(..., description="指標類型")
    forecast_days: int = Field(30, description="預測未來天數", ge=7, le=365)

class CapacityAnalysisResponse(BaseModel):
    """定義容量分析的回應格式。"""
    class CurrentUsage(BaseModel):
        """目前資源使用情況。"""
        average: Optional[float] = None
        peak: Optional[float] = None
        percentile_95: Optional[float] = Field(None, alias='95th_percentile')

    class Forecast(BaseModel):
        """資源使用預測。"""
        trend: Optional[Literal['increasing', 'stable', 'decreasing']] = None
        days_to_capacity: Optional[int] = None
        growth_rate: Optional[float] = Field(None, description="月增長率百分比")

    class Recommendation(BaseModel):
        """容量建議。"""
        type: Literal['scale_up', 'scale_down', 'optimize']
        resource: str
        priority: Literal['immediate', 'high', 'medium', 'low']
        reasoning: str

    class ChartDataPoint(BaseModel):
        """圖表資料點。"""
        date: str
        historical: Optional[float] = None
        predicted: Optional[float] = None

    current_usage: Optional[CurrentUsage] = None
    forecast: Optional[Forecast] = None
    recommendations: List[Recommendation] = []
    chart_data: List[ChartDataPoint] = []

class ExecuteRequest(BaseModel):
    """定義自然語言執行請求的資料結構。"""
    query: str = Field(..., description="自然語言查詢")
    context: Optional[Dict[str, Any]] = Field(None, description="查詢上下文")
    options: Optional[Dict[str, Any]] = Field(None, description="執行選項")

# ============================================
# Models for Skeleton Completion
# ============================================

class Pagination(BaseModel):
    """定義分頁資訊的標準結構。"""
    page: int = Field(..., description="當前頁碼")
    page_size: int = Field(..., description="每頁筆數")
    total: int = Field(..., description="總筆數")
    total_pages: int = Field(..., description="總頁數")

class DiagnosticHistoryItem(BaseModel):
    """代表一條歷史診斷記錄。"""
    session_id: uuid.UUID = Field(..., description="會話 ID")
    incident_id: Optional[str] = Field(None, description="事件 ID")
    status: str = Field(..., description="狀態")
    created_at: datetime = Field(..., description="建立時間")
    completed_at: Optional[datetime] = Field(None, description="完成時間")
    summary: Optional[str] = Field(None, description="診斷摘要")

class DiagnosticHistoryList(BaseModel):
    """代表診斷歷史記錄的列表回應。"""
    items: List[DiagnosticHistoryItem]
    pagination: Pagination

class WorkflowTemplate(BaseModel):
    """代表一個可用的工作流程模板。"""
    id: str = Field(..., description="模板 ID")
    name: str = Field(..., description="模板名稱")
    description: Optional[str] = Field(None, description="模板描述")
    parameters: List[Dict[str, Any]] = Field([], description="模板參數定義")

class ToolStatus(BaseModel):
    """代表單一診斷工具的健康狀態。"""
    status: Literal['healthy', 'unhealthy', 'unknown'] = Field(..., description="工具狀態")
    last_checked: datetime = Field(..., description="上次檢查時間")
    details: Optional[Dict[str, Any]] = Field(None, description="詳細資訊")