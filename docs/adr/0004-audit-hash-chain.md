# ADR 0004 — Server-side hash-chained audit log

- **Status:** Accepted (2026-10-30)

## Context
The prototype computed a hash chain in the browser from derived events, which proves nothing about stored history. PRD FR-AU-01 requires an immutable audit trail.

## Decision
- Table `audit_logs` is append-only: the application role has `INSERT`/`SELECT` only, and a trigger rejects `UPDATE`/`DELETE` for every role.
- Entries are chained per `chain_key` (the case id, or `org:<id>` for organisation-level events) with a monotonically increasing `seq`.
- `hash = SHA-256(prev_hash ‖ canonical_json(entry))`, genesis `prev_hash` = 64 zeros. `canonical_json` sorts keys, uses compact separators and UTF-8, and admits only strings, integers, booleans, null, lists and objects (no floats), so it is stable across implementations.
- Appends take `pg_advisory_xact_lock(hashtext(chain_key))` so concurrent writers cannot fork a chain.
- `GET /api/audit/{case_id}/verify` recomputes the chain from the stored columns and reports the first broken entry.

## Consequences
- Tampering by a database superuser is not prevented, but it is detected.
- A future step can anchor chain heads externally (e.g. periodic signed checkpoints) for non-repudiation.
