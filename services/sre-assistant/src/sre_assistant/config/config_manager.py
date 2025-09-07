# services/sre-assistant/src/sre_assistant/config/config_manager.py
"""
配置管理器
負責載入和管理應用程式配置
"""

import os
import re
import yaml
import logging
from pathlib import Path
from typing import Dict, Any, Optional
from dotenv import load_dotenv

logger = logging.getLogger(__name__)



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
        except KeyError as e:
            # 關鍵修正：當鍵不存在時，拋出 AttributeError，而不是返回空字典。
            # 這能避免隱藏設定檔缺失的問題。
            raise AttributeError(f"'{type(self).__name__}' object has no attribute '{key}'") from e

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
        初始化配置管理器。
        
        Args:
            environment (Optional[str]): 環境名稱 (例如 "development", "production", "test")。
                                         如果未提供，則從 "ENVIRONMENT" 環境變數讀取。
        """
        load_dotenv()  # 在初始化時才載入 .env，確保測試環境變數優先
        self.environment = environment or os.getenv("ENVIRONMENT", "development")
        self.config_dir = Path(__file__).parent.parent.parent.parent / "config" / "environments"
        self.config = self._load_config()
        
        logger.info(f"✅ 配置管理器初始化完成，環境: {self.environment}")

    def _deep_merge(self, source: Dict, destination: Dict) -> Dict:
        """
        遞歸地將 `source` 字典合併到 `destination` 字典中。
        """
        for key, value in source.items():
            if isinstance(value, dict) and key in destination and isinstance(destination[key], dict):
                destination[key] = self._deep_merge(value, destination[key])
            else:
                destination[key] = value
        return destination

    def _load_config(self) -> Dict[str, Any]:
        """
        載入配置檔案。

        此方法會先載入預設配置，然後讀取特定環境的 YAML 檔案，
        並將其合併到預設配置之上。最後，它會替換所有環境變數。
        
        Returns:
            一個包含最終配置的字典。
        """
        # 1. 先載入預設配置
        config = self._get_default_config()

        config_file = self.config_dir / f"{self.environment}.yaml"
        
        if config_file.exists():
            logger.info(f"正在載入環境配置檔案: {config_file}")
            try:
                with open(config_file, "r", encoding="utf-8") as f:
                    env_config = yaml.safe_load(f) or {}

                # 2. 將環境配置深度合併到預設配置上
                if env_config:
                    config = self._deep_merge(env_config, config)

            except Exception as e:
                logger.error(f"❌ 讀取或合併環境配置檔案時發生錯誤: {e}", exc_info=True)
                # 如果合併失敗，仍然繼續使用預設配置
        else:
            logger.warning(f"⚠️ 環境配置檔案不存在: {config_file}，將僅使用預設配置。")

        # 3. 對最終合併的配置進行環境變數替換
        final_config = self._substitute_env_vars(config)
        
        return final_config

    def _substitute_env_vars(self, config_value: Any) -> Any:
        """
        遞歸地替換配置值中的環境變數。

        支援 `${VAR}` 和 `${VAR:default}` 格式。
        """
        if isinstance(config_value, dict):
            return {k: self._substitute_env_vars(v) for k, v in config_value.items()}

        if isinstance(config_value, list):
            return [self._substitute_env_vars(i) for i in config_value]

        if isinstance(config_value, str):
            # 正則表達式，用於尋找所有 `${...}` 模式
            pattern = re.compile(r"\$\{(.*?)\}")

            def replace_match(match):
                # 取得括號內的內容，例如 "KEYCLOAK_URL:\"http://localhost:8080\""
                content = match.group(1)

                # 分割變數名稱和預設值
                if ":" in content:
                    var_name, default_value = content.split(":", 1)
                    # 移除預設值周圍可能存在的引號
                    default_value = default_value.strip('"\'')
                else:
                    var_name = content
                    # 如果沒有預設值，則在環境變數不存在時，保留原始字串 (例如 "${VAR}")
                    default_value = match.group(0)

                return os.getenv(var_name, default_value)

            # 使用 sub 函式進行全局替換
            return pattern.sub(replace_match, config_value)

        return config_value

    def _get_default_config(self) -> Dict[str, Any]:
        """
        獲取預設配置。

        此函式定義了在找不到環境特定設定檔時的後備設定。
        """
        return {
            "auth": {
                "provider": "keycloak",
                "keycloak": {
                    "url": os.getenv("KEYCLOAK_URL", "http://localhost:8080"),
                    "token_url": f"{os.getenv('KEYCLOAK_URL', 'http://localhost:8080')}/realms/{os.getenv('KEYCLOAK_REALM', 'sre-platform')}/protocol/openid-connect/token",
                    "realm": os.getenv("KEYCLOAK_REALM", "sre-platform"),
                    "audience": "sre-assistant",
                    "allowed_client_id": "control-plane",
                }
            },
            "control_plane": {
                "base_url": "http://localhost:8081/api/v1",
                "timeout_seconds": 20,
                "client_id": "sre-assistant",
                "client_secret": os.getenv("SRE_ASSISTANT_CLIENT_SECRET", "a_secure_secret_for_dev_only")
            },
            "prometheus": {
                "base_url": "http://localhost:9090",
                "timeout_seconds": 30,
                "default_step": "1m",
                "max_points": 11000,
            },
            "loki": {
                "base_url": "http://localhost:3100",
                "timeout_seconds": 30,
                "default_limit": 1000,
                "max_time_range": "24h",
            },
            "redis": {
                "url": os.getenv("REDIS_URL", "redis://localhost:6379/0")
            },
            "workflow": {
                "diagnosis_timeout_seconds": 120,
                "max_retries": 2,
                "retry_delay_seconds": 1
            },
            "database": {
                "url": os.getenv("DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/sre-platform")
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