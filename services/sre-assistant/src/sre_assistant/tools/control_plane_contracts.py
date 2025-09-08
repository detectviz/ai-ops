# services/sre-assistant/src/sre_assistant/tools/control_plane_contracts.py
"""
此檔案定義了與 Control Plane API 互動時使用的 Pydantic 資料契約。
這些模型確保了從 Control Plane 接收到的資料的型別安全和結構驗證。
"""

from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime

class Pagination(BaseModel):
    """
    對應 control-plane-openapi.yaml 中的 Pagination schema。
    """
    page: int
    page_size: int = Field(..., alias='pageSize')
    total: int
    total_pages: int = Field(..., alias='totalPages')
    
    class Config:
        populate_by_name = True

class Resource(BaseModel):
    """
    對應 control-plane-openapi.yaml 中的 Resource schema。
    """
    id: str
    name: str
    type: str
    status: str
    ip_address: Optional[str] = Field(None, alias='ipAddress')
    location: Optional[str] = None
    group_id: Optional[str] = Field(None, alias='groupId')
    group_name: Optional[str] = Field(None, alias='groupName')
    tags: Optional[List[str]] = None
    owner: Optional[str] = None
    description: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None
    created_at: datetime = Field(..., alias='createdAt')
    updated_at: datetime = Field(..., alias='updatedAt')

    class Config:
        populate_by_name = True # 允許使用 alias (例如 ipAddress)
        from_attributes = True # 允許從 ORM 物件轉換

class ResourceList(BaseModel):
    """
    對應 control-plane-openapi.yaml 中的 ResourceList schema。
    """
    items: List[Resource]
    pagination: Pagination

class ResourceGroup(BaseModel):
    """
    對應 control-plane-openapi.yaml 中的 ResourceGroup schema。
    """
    id: str
    name: str
    description: Optional[str] = None
    parent_group_id: Optional[str] = Field(None, alias='parentGroupId')
    resource_count: int = Field(..., alias='resourceCount')
    created_at: datetime = Field(..., alias='createdAt')
    updated_at: datetime = Field(..., alias='updatedAt')
    
    class Config:
        populate_by_name = True

class ResourceGroupList(BaseModel):
    """
    對應 control-plane-openapi.yaml 中的 ResourceGroupList schema。
    """
    items: List[ResourceGroup]
    total: int

class AlertRuleCondition(BaseModel):
    """
    對應 control-plane-openapi.yaml 中的 AlertRuleCondition schema。
    """
    metric: str
    operator: str
    threshold: float
    duration: int

class AlertRule(BaseModel):
    """
    對應 control-plane-openapi.yaml 中的 AlertRule schema。
    """
    id: str
    name: str
    description: Optional[str] = None
    condition: AlertRuleCondition
    severity: str
    enabled: bool
    notification_channels: Optional[List[str]] = Field(None, alias='notificationChannels')
    created_at: datetime = Field(..., alias='createdAt')
    updated_at: datetime = Field(..., alias='updatedAt')

    class Config:
        populate_by_name = True

class AlertRuleList(BaseModel):
    """
    對應 control-plane-openapi.yaml 中的 AlertRuleList schema。
    """
    items: List[AlertRule]
    total: int

class Execution(BaseModel):
    """
    對應 control-plane-openapi.yaml 中的 Execution schema。
    """
    id: str
    script_id: str = Field(..., alias='scriptId')
    script_name: str = Field(..., alias='scriptName')
    status: str
    parameters: Optional[Dict[str, Any]] = None
    target_resources: Optional[List[str]] = Field(None, alias='targetResources')
    output: Optional[str] = None
    error: Optional[str] = None
    started_at: Optional[datetime] = Field(None, alias='startedAt')
    completed_at: Optional[datetime] = Field(None, alias='completedAt')
    executed_by: Optional[str] = Field(None, alias='executedBy')

    class Config:
        populate_by_name = True

class ExecutionList(BaseModel):
    """
    對應 control-plane-openapi.yaml 中的 ExecutionList schema。
    """
    items: List[Execution]
    pagination: Pagination

class AuditLog(BaseModel):
    """
    對應 control-plane-openapi.yaml 中的 AuditLog schema。
    """
    id: str
    user_id: Optional[str] = Field(None, alias='userId')
    action: str
    target_resource_id: Optional[str] = Field(None, alias='targetResourceId')
    target_resource_type: Optional[str] = Field(None, alias='targetResourceType')
    status: str
    details: Optional[Dict[str, Any]] = None
    timestamp: datetime

    class Config:
        populate_by_name = True

class AuditLogList(BaseModel):
    """
    對應 control-plane-openapi.yaml 中的 AuditLogList schema。
    """
    items: List[AuditLog]
    pagination: Pagination

class Incident(BaseModel):
    """
    對應 control-plane-openapi.yaml 中的 Incident schema。
    """
    id: str
    title: str
    status: str
    severity: str
    reporter: Optional[str] = None
    assignee: Optional[str] = None
    created_at: datetime = Field(..., alias='createdAt')
    updated_at: datetime = Field(..., alias='updatedAt')

    class Config:
        populate_by_name = True

class IncidentList(BaseModel):
    """
    對應 control-plane-openapi.yaml 中的 IncidentList schema。
    """
    items: List[Incident]
    pagination: Pagination
