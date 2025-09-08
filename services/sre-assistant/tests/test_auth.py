# tests/test_auth.py
"""
對 `auth.py` 模組的單元測試
"""

import pytest
import time
import respx
from httpx import Response
from unittest.mock import MagicMock, patch
from jose import jwt
from jose.exceptions import JOSEError, JWTError, JWTClaimsError, ExpiredSignatureError

from sre_assistant.auth import decode_token, fetch_jwks, jwks_cache
from sre_assistant.dependencies import config_manager

# --- Fixtures ---

# A sample public key that our mock JWKS endpoint will serve
PUBLIC_KEY = { "kty": "RSA", "kid": "test-key-1", "use": "sig", "n": "...", "e": "AQAB" }
TOKEN_KID = "test-key-1"

@pytest.fixture(autouse=True)
def mock_config_and_cache(mocker):
    """
    自動應用的 fixture，用於模擬設定並在每次測試後清理快取。
    """
    config = MagicMock()
    config.auth.provider = "keycloak"
    config.auth.keycloak.url = "http://mock-keycloak"
    config.auth.keycloak.realm = "test-realm"
    config.auth.keycloak.audience = "sre-assistant"
    mocker.patch.object(config_manager, 'get_config', return_value=config)

    jwks_cache["keys"] = None
    jwks_cache["last_updated"] = 0
    yield config
    jwks_cache["keys"] = None
    jwks_cache["last_updated"] = 0

# --- Test Cases ---

@pytest.mark.asyncio
@respx.mock
@patch('sre_assistant.auth.jwt.decode')
@patch('sre_assistant.auth.jwk.construct')
@patch('sre_assistant.auth.jwt.get_unverified_header')
async def test_decode_token_success(mock_get_header, mock_jwk_construct, mock_jwt_decode, mock_config_and_cache):
    """測試成功解碼一個有效的 token"""
    jwks_url = f"{mock_config_and_cache.auth.keycloak.url}/realms/{mock_config_and_cache.auth.keycloak.realm}/protocol/openid-connect/certs"
    respx.get(jwks_url).mock(return_value=Response(200, json={"keys": [PUBLIC_KEY]}))

    mock_get_header.return_value = {"kid": TOKEN_KID}
    expected_payload = {"sub": "test-user"}
    mock_jwt_decode.return_value = expected_payload

    decoded_payload = await decode_token("any.valid.token")

    assert decoded_payload == expected_payload
    mock_jwt_decode.assert_called_once()

@pytest.mark.asyncio
@respx.mock
@patch('sre_assistant.auth.jwt.decode')
@patch('sre_assistant.auth.jwk.construct')
@patch('sre_assistant.auth.jwt.get_unverified_header')
async def test_decode_token_expired(mock_get_header, mock_jwk_construct, mock_jwt_decode, mock_config_and_cache):
    """測試解碼一個已過期的 token"""
    jwks_url = f"{mock_config_and_cache.auth.keycloak.url}/realms/{mock_config_and_cache.auth.keycloak.realm}/protocol/openid-connect/certs"
    respx.get(jwks_url).mock(return_value=Response(200, json={"keys": [PUBLIC_KEY]}))

    mock_get_header.return_value = {"kid": TOKEN_KID}
    mock_jwt_decode.side_effect = ExpiredSignatureError("Token has expired")

    with pytest.raises(ExpiredSignatureError):
        await decode_token("any.token.string")

@pytest.mark.asyncio
@respx.mock
@patch('sre_assistant.auth.jwt.decode')
@patch('sre_assistant.auth.jwk.construct')
@patch('sre_assistant.auth.jwt.get_unverified_header')
async def test_decode_token_invalid_signature(mock_get_header, mock_jwk_construct, mock_jwt_decode, mock_config_and_cache):
    """測試解碼一個簽名無效的 token"""
    jwks_url = f"{mock_config_and_cache.auth.keycloak.url}/realms/{mock_config_and_cache.auth.keycloak.realm}/protocol/openid-connect/certs"
    respx.get(jwks_url).mock(return_value=Response(200, json={"keys": [PUBLIC_KEY]}))

    mock_get_header.return_value = {"kid": TOKEN_KID}
    mock_jwt_decode.side_effect = JWTError("Invalid signature")

    with pytest.raises(JWTError):
        await decode_token("any.token.string")

@pytest.mark.asyncio
@respx.mock
@patch('sre_assistant.auth.jwt.decode')
@patch('sre_assistant.auth.jwk.construct')
@patch('sre_assistant.auth.jwt.get_unverified_header')
async def test_decode_token_invalid_audience(mock_get_header, mock_jwk_construct, mock_jwt_decode, mock_config_and_cache):
    """測試解碼一個 audience 不正確的 token"""
    jwks_url = f"{mock_config_and_cache.auth.keycloak.url}/realms/{mock_config_and_cache.auth.keycloak.realm}/protocol/openid-connect/certs"
    respx.get(jwks_url).mock(return_value=Response(200, json={"keys": [PUBLIC_KEY]}))

    mock_get_header.return_value = {"kid": TOKEN_KID}
    mock_jwt_decode.side_effect = JWTClaimsError("Invalid audience")

    with pytest.raises(JWTClaimsError):
        await decode_token("any.token.string")

@pytest.mark.asyncio
@respx.mock
@patch('sre_assistant.auth.jwt.get_unverified_header')
async def test_decode_token_kid_not_found(mock_get_header, mock_config_and_cache):
    """測試當 token 的 kid 在 JWKS 中找不到時的情況"""
    jwks_url = f"{mock_config_and_cache.auth.keycloak.url}/realms/{mock_config_and_cache.auth.keycloak.realm}/protocol/openid-connect/certs"
    respx.get(jwks_url).mock(return_value=Response(200, json={"keys": [{"kid": "other-key"}]}))

    mock_get_header.return_value = {"kid": "my-kid-not-in-jwks"}

    with pytest.raises(JOSEError, match="找不到對應的公鑰"):
        await decode_token("any.token.string")

@pytest.mark.asyncio
async def test_decode_token_dev_mode(mock_config_and_cache):
    """測試在 dev 模式下，會跳過驗證並返回模擬 payload"""
    mock_config_and_cache.auth.provider = "dev"

    token = "any-dev-mode-token"
    payload = await decode_token(token)

    assert payload["sub"] == "service-account-control-plane"
    assert payload["preferred_username"] == "dev_user"

@pytest.mark.asyncio
@respx.mock
async def test_jwks_caching(mock_config_and_cache):
    """測試 JWKS 金鑰快取是否正常運作"""
    jwks_url = f"{mock_config_and_cache.auth.keycloak.url}/realms/{mock_config_and_cache.auth.keycloak.realm}/protocol/openid-connect/certs"
    mock_jwks_response = {"keys": [PUBLIC_KEY]}

    route = respx.get(jwks_url).mock(return_value=Response(200, json=mock_jwks_response))

    # 第一次呼叫，應觸發 API 請求
    keys1 = await fetch_jwks(jwks_url)
    assert route.call_count == 1
    assert keys1 == [PUBLIC_KEY]

    # 第二次呼叫，應命中快取，不觸發 API 請求
    keys2 = await fetch_jwks(jwks_url)
    assert route.call_count == 1
    assert keys2 == keys1
