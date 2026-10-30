"""Canonical JSON and hash-chain primitives for the audit log (ADR 0004).

The canonical form is deliberately small: keys sorted, compact separators,
UTF-8, and only str/int/bool/None/list/dict values. Floats are rejected
because their textual form differs across languages and databases.
"""

import hashlib
import json
from collections.abc import Mapping, Sequence
from typing import Any

GENESIS_HASH = "0" * 64


class CanonicalJSONError(ValueError):
    pass


def _check(value: Any, path: str = "$") -> None:
    if value is None or isinstance(value, bool | str):
        return
    if isinstance(value, int):
        return
    if isinstance(value, float):
        raise CanonicalJSONError(f"float not allowed in audit entries at {path}; store it as a string")
    if isinstance(value, Mapping):
        for k, v in value.items():
            if not isinstance(k, str):
                raise CanonicalJSONError(f"non-string key at {path}")
            _check(v, f"{path}.{k}")
        return
    if isinstance(value, Sequence):
        for i, v in enumerate(value):
            _check(v, f"{path}[{i}]")
        return
    raise CanonicalJSONError(f"unsupported type {type(value).__name__} at {path}")


def canonical_json(value: Any) -> str:
    _check(value)
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def chain_hash(prev_hash: str, entry: Mapping[str, Any]) -> str:
    if len(prev_hash) != 64:
        raise ValueError("prev_hash must be 64 hex characters")
    return hashlib.sha256((prev_hash + canonical_json(entry)).encode("utf-8")).hexdigest()


def entry_payload(
    *,
    chain_key: str,
    seq: int,
    occurred_at: str,
    actor_id: str,
    actor_role: str,
    action: str,
    details: Mapping[str, Any],
) -> dict[str, Any]:
    """The exact fields covered by the hash."""
    return {
        "chain_key": chain_key,
        "seq": seq,
        "occurred_at": occurred_at,
        "actor_id": actor_id,
        "actor_role": actor_role,
        "action": action,
        "details": dict(details),
    }


def verify_chain(entries: Sequence[Mapping[str, Any]]) -> tuple[bool, int | None, str | None]:
    """Recomputes a chain ordered by seq.

    Each entry needs the payload fields plus ``prev_hash`` and ``hash``.
    Returns (ok, first_broken_seq, reason).
    """
    expected_prev = GENESIS_HASH
    for i, e in enumerate(entries, start=1):
        if e["seq"] != i:
            return False, int(e["seq"]), f"sequence gap: expected {i}"
        if e["prev_hash"] != expected_prev:
            return False, i, "prev_hash does not match the previous entry"
        payload = entry_payload(
            chain_key=e["chain_key"], seq=e["seq"], occurred_at=e["occurred_at"],
            actor_id=e["actor_id"], actor_role=e["actor_role"], action=e["action"], details=e["details"],
        )
        if chain_hash(e["prev_hash"], payload) != e["hash"]:
            return False, i, "hash does not match the entry content"
        expected_prev = e["hash"]
    return True, None, None
