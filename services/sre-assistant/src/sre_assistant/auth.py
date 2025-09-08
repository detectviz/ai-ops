# services/sre-assistant/src/sre_assistant/auth.py
"""
認證邏輯模組

處理 JWT Token 的驗證，包括與 Keycloak 的 JWKS 端點互動。
"""

import time
import httpx
import structlog
from typing import Dict, Any, List

from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials
from jose import jwt, jwk
from jose.exceptions import JOSEError

from .dependencies import config_manager, security

logger = structlog.get_logger(__name__)

# JWKS (JSON Web Key Set) 的記憶體快取。
# 為了避免每次驗證 token 都需要向 Keycloak 請求公鑰，我們將公鑰集快取在記憶體中。
# ttl (Time-To-Live) 設定為一小時，過期後會重新獲取。
jwks_cache = {
    "keys": None,
    "last_updated": 0,
    "ttl": 3600
}

async def fetch_jwks(jwks_url: str) -> List[Dict[str, Any]]:
    """
    從 Keycloak 的 JWKS 端點獲取公鑰集。

    實現了簡單的時間快取機制，以降低對 Keycloak 的請求頻率。

    Args:
        jwks_url: Keycloak 的 JWKS 端點 URL。

    Returns:
        一個包含多個公鑰的列表。
    """
    now = time.time()
    if jwks_cache["keys"] and (now - jwks_cache["last_updated"] < jwks_cache["ttl"]):
        return jwks_cache["keys"]

    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(jwks_url)
            response.raise_for_status()
            jwks = response.json()
            jwks_cache["keys"] = jwks.get("keys", [])
            jwks_cache["last_updated"] = now
            logger.info("✅ 成功獲取並快取 JWKS")
            return jwks_cache["keys"]
        except httpx.HTTPStatusError as e:
            logger.error(f"從 Keycloak 獲取 JWKS 失敗: {e}")
            raise HTTPException(status_code=500, detail="無法獲取認證金鑰")
        except Exception as e:
            logger.error(f"處理 JWKS 時發生未知錯誤: {e}")
            raise HTTPException(status_code=500, detail="認證服務內部錯誤")


async def decode_token(token: str) -> Dict[str, Any]:
    """
    解碼並驗證 JWT token，但不處理 FastAPI 依賴。
    這使得此函式可以在中介層等非端點的程式碼中被重複使用。
    """
    config = config_manager.get_config()
    if config.auth.provider != "keycloak":
        # 在非 keycloak 模式下，返回一個模擬的 payload
        return {"sub": "service-account-control-plane", "preferred_username": "dev_user"}

    try:
        keycloak_url = config.auth.keycloak.url
        realm = config.auth.keycloak.realm
        audience = config.auth.keycloak.audience

        jwks_url = f"{keycloak_url}/realms/{realm}/protocol/openid-connect/certs"
        jwks_keys = await fetch_jwks(jwks_url)
        if not jwks_keys:
            raise JOSEError("無法加載認證服務公鑰")

        unverified_header = jwt.get_unverified_header(token)
        kid = unverified_header.get("kid")
        if not kid:
            raise JOSEError("Token 標頭中缺少 'kid'")

        rsa_key = {}
        for key in jwks_keys:
            if key["kid"] == kid:
                rsa_key = {
                    "kty": key["kty"], "kid": key["kid"], "use": key["use"],
                    "n": key["n"], "e": key.get("e"),
                }
                break

        if not rsa_key:
            raise JOSEError("找不到對應的公鑰")

        public_key = jwk.construct(rsa_key)
        payload = jwt.decode(
            token, public_key, algorithms=["RS256"],
            audience=audience, issuer=f"{keycloak_url}/realms/{realm}"
        )
        return payload

    except (JOSEError, Exception) as e:
        # 將底層錯誤重新拋出，讓呼叫者決定如何處理 (例如，返回 HTTP 錯誤或僅記錄)
        logger.debug(f"Token 解碼失敗: {e}")
        raise e


async def verify_token(creds: HTTPAuthorizationCredentials = Depends(security)) -> Dict[str, Any]:
    """
    驗證來自 Control Plane 的 M2M JWT Token。
    這是一個 FastAPI 的依賴項 (Dependency)，會被注入到需要保護的 API 端點中。
    """
    token = creds.credentials
    try:
        payload = await decode_token(token)
        return payload
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token 已過期")
    except jwt.JWTClaimsError as e:
        raise HTTPException(status_code=401, detail=f"Token claims 錯誤: {e}")
    except JOSEError as e:
        logger.error(f"JWT 解碼/驗證錯誤: {e}", exc_info=True)
        raise HTTPException(status_code=401, detail=f"無效的 Token: {e}")
    except Exception as e:
        logger.error(f"未知的 Token 驗證錯誤: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Token 驗證時發生內部錯誤")
