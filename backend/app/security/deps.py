"""FastAPI dependencies: current user, permission checks, tenant-scoped DB connection."""

from collections.abc import Callable, Iterator
from dataclasses import dataclass

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import Connection

from app.audit.service import Actor
from app.db import org_connection
from app.security.jwt import InvalidToken, verify_token
from app.security.rbac import Permission, permissions_for

bearer = HTTPBearer(auto_error=False)


@dataclass(frozen=True)
class CurrentUser:
    id: str
    username: str
    name: str
    org_id: str
    roles: list[str]

    @property
    def primary_role(self) -> str:
        return self.roles[0] if self.roles else "none"

    @property
    def actor(self) -> Actor:
        return Actor(id=f"user:{self.username}", role=self.primary_role)


def current_user(creds: HTTPAuthorizationCredentials | None = Depends(bearer)) -> CurrentUser:
    if creds is None or creds.scheme.lower() != "bearer":
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Missing bearer token",
                            headers={"WWW-Authenticate": "Bearer"})
    try:
        c = verify_token(creds.credentials)
    except InvalidToken as exc:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid token",
                            headers={"WWW-Authenticate": "Bearer"}) from exc
    return CurrentUser(
        id=str(c["sub"]), username=str(c.get("preferred_username", "")), name=str(c.get("name", "")),
        org_id=str(c["org_id"]), roles=[str(r) for r in c.get("roles", [])],
    )


def require(permission: Permission) -> Callable[[CurrentUser], CurrentUser]:
    def checker(user: CurrentUser = Depends(current_user)) -> CurrentUser:
        if permission not in permissions_for(user.roles):
            raise HTTPException(status.HTTP_403_FORBIDDEN, f"Missing permission: {permission.value}")
        return user

    return checker


def tenant_conn(user: CurrentUser = Depends(current_user)) -> Iterator[Connection]:
    yield from org_connection(user.org_id)
