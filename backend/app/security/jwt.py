"""JWT issuance (development identity provider) and verification (ADR 0003)."""

import time
import uuid
from functools import lru_cache
from typing import Any

import jwt
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from jwt import PyJWKClient
from jwt.algorithms import RSAAlgorithm

from app.config import get_settings

KEY_ID = "mujeaz-dev-1"


@lru_cache
def _private_key() -> rsa.RSAPrivateKey:
    pem = get_settings().jwt_private_key_pem
    if pem:
        key = serialization.load_pem_private_key(pem.encode(), password=None)
        if not isinstance(key, rsa.RSAPrivateKey):
            raise ValueError("MUJEAZ_JWT_PRIVATE_KEY_PEM must be an RSA key")
        return key
    # Ephemeral key: tokens do not survive a restart. Fine for development and tests.
    return rsa.generate_private_key(public_exponent=65537, key_size=2048)


def jwks() -> dict[str, Any]:
    public_jwk = RSAAlgorithm.to_jwk(_private_key().public_key(), as_dict=True)
    public_jwk.update({"kid": KEY_ID, "use": "sig", "alg": "RS256"})
    return {"keys": [public_jwk]}


def issue_token(*, user_id: str, username: str, name: str, org_id: str, roles: list[str]) -> str:
    s = get_settings()
    now = int(time.time())
    claims = {
        "iss": s.jwt_issuer,
        "aud": s.jwt_audience,
        "sub": user_id,
        "preferred_username": username,
        "name": name,
        "org_id": org_id,
        "roles": roles,
        "iat": now,
        "nbf": now,
        "exp": now + s.jwt_ttl_minutes * 60,
        "jti": uuid.uuid4().hex,
    }
    return str(jwt.encode(claims, _private_key(), algorithm="RS256", headers={"kid": KEY_ID}))


@lru_cache
def _jwk_client(url: str) -> PyJWKClient:
    return PyJWKClient(url, cache_keys=True)


class InvalidToken(Exception):
    pass


def verify_token(token: str) -> dict[str, Any]:
    s = get_settings()
    try:
        if s.jwks_url:
            key: Any = _jwk_client(s.jwks_url).get_signing_key_from_jwt(token).key
        else:
            key = _private_key().public_key()
        claims: dict[str, Any] = jwt.decode(
            token,
            key,
            algorithms=["RS256"],
            audience=s.jwt_audience,
            issuer=s.jwt_issuer,
            options={"require": ["exp", "iat", "sub", "iss", "aud"]},
        )
    except jwt.PyJWTError as exc:
        raise InvalidToken(str(exc)) from exc
    if not claims.get("org_id"):
        raise InvalidToken("token has no org_id claim")
    if not isinstance(claims.get("roles", []), list):
        raise InvalidToken("roles claim must be a list")
    return claims
