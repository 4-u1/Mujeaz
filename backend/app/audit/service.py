"""Server-side, append-only, hash-chained audit log (PRD FR-AU-01/02, ADR 0004)."""

from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import Connection, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.sql import bindparam

from app.audit.canonical import GENESIS_HASH, chain_hash, entry_payload, verify_chain


def fmt_ts(dt: datetime) -> str:
    return dt.astimezone(UTC).isoformat(timespec="microseconds")


@dataclass(frozen=True)
class Actor:
    id: str
    role: str


SYSTEM_ACTOR = Actor(id="system", role="system")

_insert = text(
    """
    INSERT INTO audit_logs (organization_id, chain_key, seq, occurred_at, actor_id, actor_role,
                            action, details, prev_hash, hash)
    VALUES (:org, :chain_key, :seq, :occurred_at, :actor_id, :actor_role, :action, :details,
            :prev_hash, :hash)
    RETURNING id
    """
).bindparams(bindparam("details", type_=JSONB))


def append(
    conn: Connection,
    *,
    org_id: str,
    chain_key: str,
    actor: Actor,
    action: str,
    details: dict[str, Any] | None = None,
    occurred_at: datetime | None = None,
) -> dict[str, Any]:
    """Appends one entry. Serialised per chain with a transaction-scoped advisory lock."""
    details = details or {}
    conn.execute(text("SELECT pg_advisory_xact_lock(hashtext(:k))"), {"k": chain_key})
    head = conn.execute(
        text("SELECT seq, hash FROM audit_logs WHERE chain_key = :k ORDER BY seq DESC LIMIT 1"),
        {"k": chain_key},
    ).first()
    seq = (head.seq + 1) if head else 1
    prev_hash = head.hash if head else GENESIS_HASH
    ts = occurred_at or datetime.now(UTC)
    occurred = fmt_ts(ts)
    payload = entry_payload(
        chain_key=chain_key, seq=seq, occurred_at=occurred, actor_id=actor.id,
        actor_role=actor.role, action=action, details=details,
    )
    digest = chain_hash(prev_hash, payload)
    conn.execute(
        _insert,
        {
            "org": org_id, "chain_key": chain_key, "seq": seq, "occurred_at": ts,
            "actor_id": actor.id, "actor_role": actor.role, "action": action,
            "details": details, "prev_hash": prev_hash, "hash": digest,
        },
    )
    return {**payload, "prev_hash": prev_hash, "hash": digest}


def list_chain(conn: Connection, chain_key: str) -> list[dict[str, Any]]:
    rows = conn.execute(
        text(
            """
            SELECT chain_key, seq, occurred_at, actor_id, actor_role, action, details, prev_hash, hash
            FROM audit_logs WHERE chain_key = :k ORDER BY seq
            """
        ),
        {"k": chain_key},
    ).mappings()
    out = []
    for r in rows:
        d = dict(r)
        d["occurred_at"] = fmt_ts(d["occurred_at"])
        d["prev_hash"] = d["prev_hash"].strip()
        d["hash"] = d["hash"].strip()
        out.append(d)
    return out


def verify(conn: Connection, chain_key: str) -> dict[str, Any]:
    entries = list_chain(conn, chain_key)
    ok, broken_seq, reason = verify_chain(entries)
    return {
        "chain_key": chain_key,
        "entries": len(entries),
        "valid": ok,
        "first_broken_seq": broken_seq,
        "reason": reason,
        "head": entries[-1]["hash"] if entries else None,
        "algorithm": "SHA-256(prev_hash || canonical_json(entry)); genesis = 64 zeros",
    }
