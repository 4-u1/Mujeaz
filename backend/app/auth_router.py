"""Authentication endpoints: development identity provider + token introspection (ADR 0003)."""

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import Connection, text

from app.config import get_settings
from app.db import anonymous_connection
from app.security.deps import CurrentUser, current_user
from app.security.jwt import issue_token, jwks
from app.security.rbac import permissions_for
from app.seed.constants import DEMO_USERS

router = APIRouter(tags=["auth"])


@router.get("/.well-known/jwks.json")
def jwks_endpoint() -> dict[str, Any]:
    return jwks()


class DevLoginIn(BaseModel):
    username: str = Field(min_length=3, max_length=64, pattern=r"^[a-z0-9._-]+$")


def _dev_only() -> None:
    if not get_settings().dev_auth:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Not found")


@router.get("/api/auth/dev-users", dependencies=[Depends(_dev_only)])
def dev_users() -> dict[str, Any]:
    return {"users": [{"username": u.username, "name": u.display_name, "role": u.role} for u in DEMO_USERS]}


@router.post("/api/auth/dev-login", dependencies=[Depends(_dev_only)])
def dev_login(body: DevLoginIn, conn: Connection = Depends(anonymous_connection)) -> dict[str, Any]:
    row = conn.execute(text("SELECT * FROM auth_lookup_user(:u)"), {"u": body.username}).mappings().first()
    if row is None or not row["roles"]:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Unknown user")
    roles = list(row["roles"])
    token = issue_token(user_id=str(row["user_id"]), username=body.username, name=row["display_name"],
                        org_id=str(row["organization_id"]), roles=roles)
    s = get_settings()
    return {"access_token": token, "token_type": "Bearer", "expires_in": s.jwt_ttl_minutes * 60,
            "user": {"username": body.username, "name": row["display_name"], "roles": roles}}


@router.get("/api/auth/me")
def me(user: CurrentUser = Depends(current_user)) -> dict[str, Any]:
    return {"id": user.id, "username": user.username, "name": user.name, "org_id": user.org_id,
            "roles": user.roles, "permissions": sorted(p.value for p in permissions_for(user.roles))}
