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
