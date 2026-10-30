"""Database access.

Every request runs in one transaction on the *application* role, with the
caller's organisation bound through ``set_config('app.org_id', …, true)``.
PostgreSQL Row-Level Security policies read that setting, so tenant isolation
holds even if a query forgets an ``organization_id`` filter.
"""

from collections.abc import Iterator
from functools import lru_cache

from sqlalchemy import Connection, Engine, create_engine, text

from app.config import get_settings


@lru_cache
def get_engine() -> Engine:
    return create_engine(get_settings().database_url, pool_pre_ping=True, future=True)


@lru_cache
def get_owner_engine() -> Engine:
    return create_engine(get_settings().owner_database_url, pool_pre_ping=True, future=True)


def bind_org(conn: Connection, org_id: str) -> None:
    conn.execute(text("SELECT set_config('app.org_id', :org, true)"), {"org": str(org_id)})


def org_connection(org_id: str) -> Iterator[Connection]:
    """Yields a transactional connection scoped to one organisation."""
    with get_engine().begin() as conn:
        bind_org(conn, org_id)
        yield conn


def anonymous_connection() -> Iterator[Connection]:
    """Connection without an organisation (RLS returns no tenant rows)."""
    with get_engine().begin() as conn:
        yield conn
