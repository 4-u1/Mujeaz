# Mujeaz — Architecture (M2)

> Status: milestone **M2 Intelligence**. A1, A2 and A3 are real for MRI Lumbar Spine (ADR 0005, 0006); A4 and A6 follow in M4–M5. Roadmap: `docs/PRD.md §17`, `docs/M2_PLAN.md`.

## 1. Components

```
 Browser ──► nginx (frontend container :8080)
              ├─ /            React 19 + Vite build (Arabic RTL first)
              └─ /api, /.well-known, /healthz ──► FastAPI (backend :8000)
                                                   ├─ auth_router     dev IdP, JWKS, /me
                                                   ├─ cases.router    cases, twins, transitions, metrics, audit
                                                   ├─ orchestrator    POST /api/cases/{id}/analyze (JSON or SSE)
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
| `backend/app/agents/` | A1 baseline + LLM extractors, span verifier, number parser, A2 evidence hunter, A5 readiness, injection detector |
| `backend/app/rules/` | YAML policy rules engine; `policies/*.yaml` are versioned with their source text |
| `backend/app/llm/`, `app/prompts/` | Provider interface (Gemini, Replay), versioned prompt files |
| `backend/app/nlp/` | Arabic/English normalisation with offset maps, sentence chunker |
| `backend/app/orchestrator/` | Pure pipeline (`core.py`, shared with evals) and persistence service + route |
| `evals/run.py` | Eval runner: metrics per split/scenario/language, gates, JSON + Markdown report |
| `backend/app/ai/` | LLM calls with delimited untrusted text and deterministic scoring |
| `backend/app/seed/` | Demo organisations, users, payers, policy, legacy and synthetic cases |
| `backend/migrations/` | Alembic; `0001` schema, roles, RLS, triggers; `0002` chunks, analysis runs, provenance |
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

## 5. Analysis pipeline (M2)

```
load case + all patient documents (FOR UPDATE) ─► index chunks
  ─► A1 extract (baseline | LLM) ─► verifier: quote → offsets, reject if absent
  ─► injection flags (recorded, never decisive)
  ─► A2 BM25 retrieval + FOUND/PARTIAL/MISSING + CDI question
  ─► A3 YAML rules ─► A5 readiness + revenue risk
  ─► replace current facts/requirements/evidence, keep full result in analysis_runs
  ─► transition (RISK_DETECTED | DECISION_READY) ─► audit entries        — one transaction
```

## 6. What is real and what is simulated

| Capability | State |
|---|---|
| Persistence, auth, RBAC, RLS, audit chain | **Real** |
| Readiness and revenue formulas | **Real** (deterministic) |
| Synthetic dataset and ground truth | **Real** (synthetic data) |
| A1 / A2 / A3 | **Real** for MRI Lumbar Spine with Demo Payer A policy v2026.1; quality measured on synthetic data only |
| Legacy "Evidence Hunter" demo button | Kept for the two legacy demo cases without an agent analysis |
| FHIR | Sample payloads, not validated; builder and validator in M4 |
| Payer / NPHIES | **Simulated** and labelled everywhere |
| LLM analysis | Gemini if `GEMINI_API_KEY` is set, otherwise labelled fallback |
