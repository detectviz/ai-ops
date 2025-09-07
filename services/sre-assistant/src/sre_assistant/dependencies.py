# services/sre-assistant/src/sre_assistant/dependencies.py
"""
共享依賴項模組

此模組用於初始化並提供應用程式範圍內的共享實例，
例如設定管理器和安全方案，以避免循環導入問題。
"""

from fastapi.security import HTTPBearer
from .config.config_manager import ConfigManager

# 初始化設定管理器，應用程式將從這裡獲取所有設定
config_manager = ConfigManager()

# 初始化 HTTP Bearer 安全方案，用於 API 端點的依賴注入
security = HTTPBearer()
