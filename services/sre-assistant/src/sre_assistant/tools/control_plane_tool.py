# services/sre-assistant/src/sre_assistant/tools/control_plane_tool.py
"""
Control Plane 整合工具
用於回調 Control Plane API 獲取審計日誌和變更歷史
"""

import logging
import httpx
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta, timezone
import jwt
import time

from ..contracts import ToolResult, ToolError

logger = logging.getLogger(__name__)


class ControlPlaneTool:
    """
    Control Plane API 整合工具
    
    功能：
    - 查詢審計日誌
    - 獲取服務變更歷史
    - 查詢告警事件
    - 獲取自動化執行紀錄
    """
    
    def __init__(self, config):
        """初始化 Control Plane 工具"""
        self.base_url = config.control_plane.get("base_url", "http://control-plane:8081/api")
        self.timeout = config.control_plane.get("timeout_seconds", 10)
        
        # M2M 認證設定
        self.client_id = config.control_plane.get("client_id", "sre-assistant")
        self.client_secret = config.control_plane.get("client_secret", "")
        self.token = None  # JWT token 快取
        self.token_expires_at = None  # token 到期時間