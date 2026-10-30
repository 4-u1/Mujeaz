"""Operational commands.

    python -m app.cli migrate     # alembic upgrade head (owner connection)
    python -m app.cli app-role    # enable login for the application role with MUJEAZ_APP_DB_PASSWORD
    python -m app.cli seed [--reset]
    python -m app.cli bootstrap   # all of the above, idempotent
"""

import argparse
import json
import logging
from pathlib import Path

from alembic import command
from alembic.config import Config

from app.config import get_settings
from app.db import get_owner_engine
from app.observability import configure_logging
from app.seed.load import seed

BACKEND_DIR = Path(__file__).resolve().parents[1]
log = logging.getLogger("mujeaz.cli")


def migrate() -> None:
    cfg = Config(str(BACKEND_DIR / "alembic.ini"))
    cfg.set_main_option("script_location", str(BACKEND_DIR / "migrations"))
    command.upgrade(cfg, "head")


def enable_app_role() -> None:
    pw = get_settings().app_db_password.replace("'", "''")
    with get_owner_engine().begin() as conn:
        # ALTER ROLE does not accept bind parameters; the value is quoted above.
        conn.exec_driver_sql(f"ALTER ROLE mujeaz_app WITH LOGIN PASSWORD '{pw}'")


def run_seed(reset: bool) -> dict[str, int]:
    with get_owner_engine().begin() as conn:
        result = seed(conn, reset=reset)
    log.info("seed complete", extra={"extra_fields": result})
    return result


def main() -> None:
    configure_logging()
    p = argparse.ArgumentParser(prog="mujeaz")
    sub = p.add_subparsers(dest="cmd", required=True)
    sub.add_parser("migrate")
    sub.add_parser("app-role")
    s = sub.add_parser("seed")
    s.add_argument("--reset", action="store_true")
    b = sub.add_parser("bootstrap")
    b.add_argument("--reset", action="store_true")
    args = p.parse_args()
    if args.cmd == "migrate":
        migrate()
    elif args.cmd == "app-role":
        enable_app_role()
    elif args.cmd == "seed":
        print(json.dumps(run_seed(args.reset)))
    elif args.cmd == "bootstrap":
        migrate()
        enable_app_role()
        print(json.dumps(run_seed(args.reset)))


if __name__ == "__main__":
    main()
