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
    incident_id: str = Field(..., description="事件 ID")
    severity: Literal['P0', 'P1', 'P2', 'P3'] = Field(..., description="嚴重程度")
    title: Optional[str] = Field(None, description="事件標題")
    description: Optional[str] = Field(None, description="問題描述")
    affected_services: List[str] = Field(..., description="受影響的服務列表")
    time_range: Optional[Dict[str, datetime]] = Field(None, description="時間範圍")
    context: Dict[str, Any] = Field({}, description="額外上下文資訊")

class DiagnosticResponse(BaseModel):
    session_id: uuid.UUID = Field(..., description="診斷會話 ID")
    status: Literal['accepted'] = Field("accepted", description="狀態")
    message: Optional[str] = Field(None, description="狀態訊息")
    estimated_time: Optional[int] = Field(None, description="預估完成時間（秒）")

class Finding(BaseModel):
    source: str = Field(..., description="發現來源（如 Prometheus, Loki）")
    severity: Literal['critical', 'warning', 'info'] = Field(..., description="嚴重程度")
    message: str = Field(..., description="發現描述")
    evidence: Optional[Dict[str, Any]] = Field(None, description="支撐證據")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="時間戳")

class DiagnosticResult(BaseModel):
    summary: Optional[str] = Field(None, description="診斷摘要")
    findings: List[Finding] = Field([], description="發現列表")
    recommended_actions: List[str] = Field([], description="建議採取的行動")
    confidence_score: Optional[float] = Field(None, description="診斷信心分數", ge=0, le=1)
    tools_used: List[str] = Field([], description="使用的診斷工具")
    execution_plan: Optional[List[str]] = Field(None, description="執行的診斷步驟計畫")
    execution_time: Optional[float] = Field(None, description="執行時間（秒）")

class DiagnosticStatus(BaseModel):
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
    code: str
    message: str
    details: Optional[Dict[str, Any]] = None

class ToolResult(BaseModel):
    success: bool
    data: Optional[Dict[str, Any]] = None
    error: Optional[ToolError] = None