import pytest

pytest.importorskip("pydantic_settings")
jwt = pytest.importorskip("jwt")

from app.security.jwt import InvalidToken, issue_token, jwks, verify_token  # noqa: E402


def test_round_trip() -> None:
    tok = issue_token(user_id="u1", username="sara.auth", name="Sara", org_id="o1", roles=["auth_officer"])
    claims = verify_token(tok)
    assert claims["sub"] == "u1" and claims["org_id"] == "o1" and claims["roles"] == ["auth_officer"]


def test_tampered_token_is_rejected() -> None:
    tok = issue_token(user_id="u1", username="sara.auth", name="Sara", org_id="o1", roles=["auth_officer"])
    head, body, sig = tok.split(".")
    forged = jwt.encode({"sub": "u1", "org_id": "o2", "roles": ["rcm_manager"]}, "secret", algorithm="HS256")
    with pytest.raises(InvalidToken):
        verify_token(forged)
    with pytest.raises(InvalidToken):
        verify_token(f"{head}.{body}.{sig[::-1]}")


def test_jwks_publishes_public_key_only() -> None:
    key = jwks()["keys"][0]
    assert key["kty"] == "RSA" and key["alg"] == "RS256"
    assert "d" not in key and "p" not in key
