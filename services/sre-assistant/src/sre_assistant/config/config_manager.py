# services/sre-assistant/src/sre_assistant/config/config_manager.py
"""
配置管理器
負責載入和管理應用程式配置
"""

import os
import yaml
import logging
from pathlib import Path
from typing import Dict, Any, Optional
from pydantic import BaseModel, Field
from dotenv import load_dotenv

logger = logging.getLogger(__name__)

# 載入環境變數
load_dotenv()


class DotDict(dict):
    """
    支援點號訪問的字典

    允許使用 config.auth.provider 而不是 config["auth"]["provider"]
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for key, value in self.items():
            if isinstance(value, dict):
                self[key] = DotDict(value)

    def __getattr__(self, key):
        try:
            return self[key]
        except KeyError:
            # 返回空的 DotDict 而不是拋出異常
            return DotDict()

    def __setattr__(self, key, value):
        self[key] = value

    def get(self, key, default=None):
        """
        安全獲取值

        支援點號分隔的鍵
        """
        if "." in key:
            keys = key.split(".")
            value = self
            for k in keys:
                if isinstance(value, dict):
                    value = value.get(k)
                    if value is None:
                        return default
                else:
                    return default
            return value
        else:
            return super().get(key, default)


class ConfigManager:
    """
    配置管理器
    
    支援從 YAML 檔案和環境變數載入配置
    """
    
    def __init__(self, environment: Optional[str] = None):
        """
        初始化配置管理器
        
        Args:
            environment: 環境名稱 (development/production/test)
        """
        self.environment = environment or os.getenv("ENVIRONMENT", "development")
        self.config_dir = Path(__file__).parent / "environments"
        self.config = self._load_config()
        
        logger.info(f"✅ 配置管理器初始化: environment={self.environment}")
    
    def _load_config(self) -> Dict[str, Any]:
        """
        載入配置檔案
        
        Returns:
            配置字典
        """
        config_file = self.config_dir / f"{self.environment}.yaml"
        
        if not config_file.exists():
            logger.warning(f"配置檔案不存在: {config_file}，使用預設配置")
            return self._get_default_config()
        
        try:
            with open(config_file, "r", encoding="utf-8") as f:
                config = yaml.safe_load(f)
            
            # 替換環境變數
            config = self._substitute_env_vars(config)
            
            logger.info(f"✅ 載入配置檔案: {config_file}")
            return config
            
        except Exception as e:
            logger.error(f"載入配置檔案失敗: {e}")
            return self._get_default_config()
    
    def _substitute_env_vars(self, config: Any) -> Any:
        """
        替換配置中的環境變數
        
        支援 ${ENV_VAR} 格式
        """
        if isinstance(config, dict):
            result = {}
            for key, value in config.items():
                result[key] = self._substitute_env_vars(value)
            return result
        elif isinstance(config, list):
            return [self._substitute_env_vars(item) for item in config]
        elif isinstance(config, str):
            # 檢查是否包含環境變數
            if config.startswith("${") and config.endswith("}"):
                env_var = config[2:-1]
                return os.getenv(env_var, config)
            return config
        else:
            return config
    
    def _get_default_config(self) -> Dict[str, Any]:
        """
        獲取預設配置。

        此函式定義了在找不到環境特定設定檔 (如 development.yaml) 時的後備設定。
        這主要用於本地開發和測試，確保服務在最基本的環境下也能啟動。
        
        Returns:
            一個包含預設設定的字典。
        """
        return {
            "deployment": {
                "platform": "local",
                "debug": True,
                "host": "0.0.0.0",
                "port": 8000
            },
            "sre_assistant": {
                "base_url": "http://localhost:8000"
            },
            "memory": {
                "backend": "memory",
                "postgres_connection_string": os.getenv(
                    "DATABASE_URL",
                    "postgresql://postgres:postgres@localhost:5432/sre_assistant"
                )
            },
            "session_backend": "memory",
            "auth": {
                "provider": "none",
                "enable_rbac": False,
                "enable_rate_limiting": False,
                "keycloak": {
                    "token_url": "http://localhost:8080/realms/sre-platform/protocol/openid-connect/token"
                }
            },
            "control_plane": {
                "base_url": "http://localhost:8081/api",
                "timeout_seconds": 10,
                "client_id": "sre-assistant",
                "client_secret": os.getenv("SRE_ASSISTANT_CLIENT_SECRET", "")
            },
            "prometheus": {
                "base_url": "http://localhost:9090",
                "timeout_seconds": 15,
                "default_step": "1m",
                "max_points": 1000
            },
            "loki": {
                "base_url": "http://localhost:3100",
                "timeout_seconds": 20,
                "default_limit": 1000,
                "max_time_range": "24h"
            },
            "workflow": {
                "parallel_diagnosis": True,
                "diagnosis_timeout_seconds": 60,
                "max_retries": 3
            },
            "logging": {
                "level": "INFO",
                "format": "json"
            }
        }
    
    def get_config(self) -> DotDict:
        """
        獲取配置（支援點號訪問）
        
        Returns:
            配置物件
        """
        return DotDict(self.config)
    
    def get(self, key: str, default: Any = None) -> Any:
        """
        獲取配置項
        
        Args:
            key: 配置鍵（支援點號分隔）
            default: 預設值
            
        Returns:
            配置值
        """
        keys = key.split(".")
        value = self.config
        
        for k in keys:
            if isinstance(value, dict):
                value = value.get(k)
                if value is None:
                    return default
            else:
                return default
        
        return value
    
    def update(self, key: str, value: Any):
        """
        更新配置項
        
        Args:
            key: 配置鍵（支援點號分隔）
            value: 新值
        """
        keys = key.split(".")
        config = self.config
        
        for k in keys[:-1]:
            if k not in config:
                config[k] = {}
            config = config[k]
        
        config[keys[-1]] = value
        logger.info(f"更新配置: {key} = {value}")
    
    def reload(self):
        """重新載入配置"""
        self.config = self._load_config()
        logger.info("✅ 配置已重新載入")