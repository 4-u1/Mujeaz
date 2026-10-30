"""Integration fixtures. Require a PostgreSQL 16 + pgvector database.

Set MUJEAZ_RUN_INTEGRATION=1 plus MUJEAZ_OWNER_DATABASE_URL (superuser/owner) and
MUJEAZ_DATABASE_URL (the mujeaz_app role, password MUJEAZ_APP_DB_PASSWORD).
"""

import os
from collections.abc import Iterator

import pytest

if not os.environ.get("MUJEAZ_RUN_INTEGRATION"):
    pytest.skip("integration tests disabled (set MUJEAZ_RUN_INTEGRATION=1)", allow_module_level=True)

from alembic import command  # noqa: E402
from alembic.config import Config  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from app.cli import BACKEND_DIR, enable_app_role, run_seed  # noqa: E402

pytestmark = pytest.mark.integration


def _alembic() -> Config:
    cfg = Config(str(BACKEND_DIR / "alembic.ini"))
    cfg.set_main_option("script_location", str(BACKEND_DIR / "migrations"))
    return cfg


@pytest.fixture(scope="session", autouse=True)
def database() -> Iterator[None]:
    cfg = _alembic()
    command.upgrade(cfg, "head")
    command.downgrade(cfg, "base")  # proves the downgrade path
    command.upgrade(cfg, "head")
    enable_app_role()
    counts = run_seed(reset=True)
    assert counts["legacy_cases"] == 3 and counts["synthetic_cases"] == 50
    yield


@pytest.fixture(scope="session")
def client(database: None) -> TestClient:
    from app.main import create_app

    return TestClient(create_app())


@pytest.fixture(scope="session")
def login(client: TestClient):  # type: ignore[no-untyped-def]
    cache: dict[str, dict[str, str]] = {}

    def _login(username: str) -> dict[str, str]:
        if username not in cache:
            r = client.post("/api/auth/dev-login", json={"username": username})
            assert r.status_code == 200, r.text
            cache[username] = {"Authorization": f"Bearer {r.json()['access_token']}"}
        return cache[username]

    return _login
