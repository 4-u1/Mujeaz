import pytest

from app.audit.canonical import (
    GENESIS_HASH,
    CanonicalJSONError,
    canonical_json,
    chain_hash,
    entry_payload,
    verify_chain,
)


def _chain(n: int) -> list[dict]:
    out, prev = [], GENESIS_HASH
    for i in range(1, n + 1):
        p = entry_payload(chain_key="c", seq=i, occurred_at=f"2026-10-30T00:00:0{i}.000000+00:00",
                          actor_id="user:sara", actor_role="auth_officer", action="x", details={"i": i, "ar": "نعم"})
        h = chain_hash(prev, p)
        out.append({**p, "prev_hash": prev, "hash": h})
        prev = h
    return out


def test_canonical_is_key_order_independent_and_compact() -> None:
    assert canonical_json({"b": 1, "a": [True, None, "x"]}) == '{"a":[true,null,"x"],"b":1}'
    assert canonical_json({"a": 1, "b": 2}) == canonical_json({"b": 2, "a": 1})


def test_canonical_keeps_arabic_as_utf8() -> None:
    assert canonical_json({"m": "نعم"}) == '{"m":"نعم"}'


def test_floats_are_rejected() -> None:
    with pytest.raises(CanonicalJSONError):
        canonical_json({"value": 1.5})


def test_valid_chain_verifies() -> None:
    assert verify_chain(_chain(5)) == (True, None, None)


def test_content_tamper_is_detected_at_the_edited_entry() -> None:
    c = _chain(5)
    c[2]["details"] = {"i": 999, "ar": "نعم"}
    ok, seq, reason = verify_chain(c)
    assert (ok, seq) == (False, 3) and "content" in reason


def test_deleted_entry_is_detected() -> None:
    c = _chain(5)
    del c[1]
    ok, seq, _ = verify_chain(c)
    assert not ok and seq is not None


def test_relinked_chain_is_detected() -> None:
    c = _chain(3)
    c[1]["prev_hash"] = GENESIS_HASH
    assert verify_chain(c)[0] is False
