# Mujeaz — Architecture (M1)

> Status: milestone **M1 Foundation**. Agents A1–A6 are not yet real retrieval/reasoning services; see the roadmap in `docs/PRD.md §17` and `docs/IMPLEMENTATION_PLAN.md`.

## 1. Components

```
 Browser ──► nginx (frontend container :8080)
              ├─ /            React 19 + Vite build (Arabic RTL first)
              └─ /api, /.well-known, /healthz ──► FastAPI (backend :8000)
                                                   ├─ auth_router     dev IdP, JWKS, /me
                                                   ├─ cases.router    cases, twins, transitions, metrics, audit
                                                   ├─ ai.router       analyze-order, generate-appeal (Gemini)
                                                   └─ PostgreSQL 16 + pgvector (db :5432)
```

| Path | Responsibility |
|---|---|
| `backend/app/config.py` | Settings from `MUJEAZ_*` environment variables; refuses dev auth in production |
| `backend/app/db.py` | Engines; every request runs in one transaction with `app.org_id` bound |
| `backend/app/security/` | JWT issue/verify (RS256), RBAC matrix, FastAPI dependencies |
| `backend/app/audit/` | Canonical JSON, hash chain, append/list/verify |
| `backend/app/scoring/` | Python port of `shared/scoring.ts` (parity-tested) |
| `backend/app/cases/` | State machine, repository (twin view, metrics), HTTP routes |
| `backend/app/ai/` | LLM calls with delimited untrusted text and deterministic scoring |
| `backend/app/seed/` | Demo organisations, users, payers, policy, legacy and synthetic cases |
| `backend/migrations/` | Alembic; `0001` creates schema, roles, RLS, triggers |
| `evals/generator/` | Deterministic synthetic FHIR dataset with ground truth |
| `shared/` | TypeScript scoring reference + `scoring_vectors.json` |
| `frontend/` | React app; `src/api/client.ts` is the only network layer |
| `infra/` | docker compose, nginx config |

## 2. Request lifecycle

1. The browser sends `Authorization: Bearer <JWT>`.
2. `current_user` verifies signature, issuer, audience and expiry, then reads `org_id` and `roles`.
3. `require(permission)` checks the RBAC matrix.
4. `tenant_conn` opens a transaction as `mujeaz_app` and runs `set_config('app.org_id', <org>, true)`.
5. Queries run under Row-Level Security; rows of other organisations are invisible and cannot be written.
6. State changes append to the audit chain in the same transaction, so data and audit commit or roll back together.

## 3. Data model

PRD §10 is implemented in full by migration `0001`. Highlights:

- **Tenancy:** `organization_id` on every tenant table, with RLS policy `tenant_isolation`.
- **Case:** `authorization_requests` plus `authorization_requirements`, `authorization_evidence`, `clinical_facts`, `readiness_scores` and `revenue_risk`. Scores and risk are append-only histories; the latest row wins.
- **Lifecycle:** `authorization_events` records transitions; `human_reviews` records the human gates (submission, appeal).
- **Clinical record:** `patients`, `encounters`, `clinical_documents` (with a SHA-256 of the content), `evidence_spans`.
- **Policy:** `payers`, `payer_policies`, `policy_versions` (source text + hash), `policy_rules` (`spec` JSON for the future rules engine), `policy_chunks` (`vector(768)` for RAG in M2).
- **Agents:** `agent_runs` (model, prompt version, input hash, output, latency, tokens, cost), `prompts`.
- **Audit:** `audit_logs` (ADR 0004).

## 4. Case state machine

```
DRAFT ─► RISK_DETECTED ─► EVIDENCE_SEARCHING ─► DECISION_READY ══(human: SUBMISSION)══► SUBMITTED
  └──────────────► DECISION_READY ◄─────────────────┘                                    │
                                                                         APPROVED ◄──────┤
                                                                         DENIED ◄────────┘
DENIED ─► RECOVERY_IN_PROGRESS ⇄ APPEAL_READY ══(human: APPEAL)══► RECOVERED
```

Each edge declares the permission it needs (`backend/app/cases/state_machine.py`). Anything not in the table returns **409**.

## 5. What is real and what is simulated in M1

| Capability | M1 state |
|---|---|
| Persistence, auth, RBAC, RLS, audit chain | **Real** |
| Readiness and revenue formulas | **Real** (deterministic) |
| Synthetic dataset and ground truth | **Real** (synthetic data) |
| Evidence Hunter | Demo: applies only evidence stored with the legacy demo case; real retrieval in M2 |
| Policy reasoning | Seeded demo policy and requirements; rules engine in M2 |
| FHIR | Sample payloads, not validated; builder and validator in M4 |
| Payer / NPHIES | **Simulated** and labelled everywhere |
| LLM analysis | Gemini if `GEMINI_API_KEY` is set, otherwise labelled fallback |
