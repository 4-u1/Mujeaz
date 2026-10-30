import pytest

pytest.importorskip("pydantic_settings")

from app.config import Settings  # noqa: E402


def test_dev_auth_is_off_by_default(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("MUJEAZ_DEV_AUTH", raising=False)
    assert Settings(_env_file=None).dev_auth is False


def test_production_refuses_dev_auth() -> None:
    with pytest.raises(ValueError, match="MUJEAZ_DEV_AUTH"):
        Settings(_env_file=None, env="production", dev_auth=True)


def test_production_without_dev_auth_is_allowed() -> None:
    assert Settings(_env_file=None, env="production", dev_auth=False).env == "production"
