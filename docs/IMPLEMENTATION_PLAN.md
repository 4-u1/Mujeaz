# Mujeaz — Implementation Plan

| | |
|---|---|
| Scope of this revision | **M1 — Foundation** (detailed). M2–M4 outlined for sequencing only. |
| Baseline | `main` @ `fc2b11a` (M0 complete) |
| Author | Yazeed Hamad Alharthi |
| Status | **Approved 2026-10-30 (D1–D7 as recommended). M1 in progress on `feat/m1-foundation`.** |

---

## 1. Understanding of the current system

The repository is a single Vite + React 19 app with an Express server (`server.ts`) that exposes two Gemini endpoints (`/api/ai/analyze-order`, `/api/ai/generate-appeal`) with schema-light validation, a per-IP rate limiter and a labelled fallback mode. Readiness Score, denial risk and revenue figures are computed deterministically in `shared/scoring.ts` (weights 30/25/15/15/10/5, gates 60/50, labels ≥90 / 70–89 / <70). The domain model lives in `src/types.ts` (`ClaimDigitalTwin` and friends). All case data are three synthetic cases in `src/data/mockCases.ts`, held in React state. The Evidence Hunter is a state transition that applies `discoverableEvidence` from the demo data. The audit log is a SHA-256 chain computed in the browser from derived events, so it proves nothing about persisted history. There is no database, no authentication, no tests and no CI. FHIR payloads are static samples (`Claim` with `use: preauthorization`, `ClaimResponse` for the denial) using demo code systems. The PRD defines the target: FastAPI services, PostgreSQL with RLS and pgvector, a rules engine, a server-side hash-chained audit log, and an evaluated agent pipeline (FR-A1…FR-A6, FR-HR, FR-AU).

---

## 2. M1 objective and exit criteria

**Objective:** a persistent, authenticated, auditable foundation on which agents can be built in M2 — with no AI behaviour change yet.

**Exit criteria (all must be true):**
1. `docker compose up` starts `db` (PostgreSQL 16 + pgvector), `backend` (FastAPI) and `frontend` (Vite build served by nginx), runs migrations and loads the seed.
2. The UI lists and opens cases **from the database** through the new API; the three legacy demo cases are migrated as seed data.
3. Every endpoint requires a JWT; role checks are enforced and tested for all six roles.
4. Audit entries are written server-side for every state change; `GET /api/audit/{case_id}/verify` recomputes the chain; a test proves tampering is detected.
5. 50 synthetic MRI Lumbar Spine FHIR bundles with ground-truth annotations are generated reproducibly from a seed.
6. CI is green on GitHub Actions: lint, type-check, unit + integration tests (Postgres service container), Docker build.

---

## 3. Work breakdown — M1

Estimates are focused engineering days (d) for one engineer.

| ID | Task | PRD refs | Est. | Output / acceptance |
|---|---|---|---:|---|
| **M1-01** | Repo restructure: move the app to `frontend/`, create `backend/`, `infra/`, `evals/`, `shared/` (kept). Root `Makefile` and updated README run instructions. | §9 | 0.5d | App still builds and runs from `frontend/`. No behaviour change. |
| **M1-02** | ADR-001 Backend language (Python/FastAPI), ADR-002 Monorepo layout, ADR-003 Auth model, ADR-004 Audit chain design. | §9 | 0.5d | `docs/adr/0001…0004.md` |
| **M1-03** | Backend skeleton: FastAPI app factory, settings via `pydantic-settings`, structured JSON logging with correlation ID middleware, `/healthz`, `/readyz`, error envelope, CORS. `uv` for dependency locking. | §11 | 1d | Health endpoints pass tests; logs carry `request_id`. |
| **M1-04** | Data model and Alembic migrations for: `organizations, facilities, users, roles, user_roles, patients, encounters, clinical_documents, clinical_facts, evidence_spans, payers, payer_policies, policy_versions, policy_rules, policy_chunks(embedding vector), authorization_requests, authorization_requirements, authorization_evidence, authorization_events, readiness_scores, revenue_risk, price_lists, claims, denials, denial_reasons, appeals, appeal_evidence, recovery_cases, deadlines, agent_runs, prompts, human_reviews, audit_logs, nphies_transactions`. UUID PKs, `organization_id` on every tenant table, `created_at/updated_at`, soft-delete where needed. | §10, FR-AU-02 | 2d | `alembic upgrade head` on empty DB succeeds; downgrade to base succeeds. |
| **M1-05** | Row-Level Security: policies keyed on `current_setting('app.org_id')`, set per request in a DB session hook; a non-superuser app role. | §10, §12 | 1d | Test: user of org A cannot read or write org B rows, even with a crafted ID. |
| **M1-06** | Auth: local dev identity provider issuing RS256 JWTs (`sub`, `org_id`, `roles`), JWKS endpoint, token verification dependency; OIDC-ready config so a real IdP can replace it. Seeded demo users, one per role. | §12, FR-HR-01 | 1.5d | Unauthenticated → 401; wrong role → 403; tokens expire. |
| **M1-07** | RBAC: permission matrix (`case:read`, `case:analyze`, `case:approve_submission`, `appeal:draft`, `appeal:approve`, `audit:read`, `admin:*`) mapped to the six roles; a `require(permission)` dependency. | §4, §12 | 1d | Matrix test covers every role × permission. |
| **M1-08** | Audit service: append-only table (no UPDATE/DELETE grants), per-case chain `hash = SHA-256(prev_hash ‖ canonical_json(entry))` with RFC 8785 JSON canonicalisation, genesis per case, row lock to serialise appends. `GET /api/audit/{case_id}` and `/verify`. | FR-AU-01, FR-AU-02 | 1.5d | Concurrent append test keeps chain valid; tamper test (edit a past row as superuser) → `verify` reports the first broken index. |
| **M1-09** | Case API (read-only + state): list with filters and pagination, case detail (facts, rules, evidence, scores, events), transition endpoint guarded by the case state machine (DRAFT → … → APPROVED/DENIED → RECOVERY…). Every transition writes audit. | §6, §7 | 1.5d | Contract tests from OpenAPI; illegal transitions rejected with 409. |
| **M1-10** | Scoring port: `backend/scoring/` in Python, plus `shared/scoring_vectors.json` generated from the TypeScript module; parity test in both Vitest and pytest. | §8, FR-A5-01 | 1d | 100% parity on ≥ 200 vectors including gate edges. |
| **M1-11** | Synthetic data generator (`evals/generator/`): deterministic (seeded) FHIR R4 bundles for 50 MRI Lumbar Spine cases. Notes built from bilingual templates (Arabic, English, mixed). Ground truth is produced **by construction** alongside each bundle (facts with exact offsets, expected evidence status per requirement, expected rule outcome, expected score). Scenario mix: found-in-other-encounter, partial (duration < 6 weeks), missing, contradictory notes, red-flag exemption, wrong/incompatible coding, Arabic-only notes, injection text inside a note. | §13 | 3d | `make data` reproduces byte-identical output; schema-valid bundles; annotation coverage report. |
| **M1-12** | Seeder: loads bundles into the relational model and the three legacy demo cases; demo payers A/B/C; demo price list (MRI lumbar 2,800 SAR). | §8.2 | 1d | Fresh `compose up` shows 53 cases in the UI. |
| **M1-13** | Frontend wiring: TanStack Query client, login screen (dev IdP), Command Center and Digital Twin read from the API; audit tab reads the server chain and calls `/verify`. Remove `src/data/mockCases.ts` usage from runtime paths. Express server removed. | §7.8 | 2.5d | Playwright smoke: login → list → open case → verify audit. |
| **M1-14** | Infra: `infra/docker-compose.yml` (pgvector/pgvector:pg16, backend, frontend via nginx), healthchecks, `.env.example`, non-root containers. | §11 | 1d | `docker compose up` green from a clean clone. |
| **M1-15** | CI (GitHub Actions): ruff, mypy (strict on `scoring`, `audit`, `security`), pytest with Postgres service container and coverage, eslint, `tsc --noEmit`, Vitest, Docker build, `pip-audit` + `npm audit` (report-only). | §7 | 1d | Green pipeline on the M1 PR; coverage ≥ 80% on `scoring/`, `audit/`, `security/`. |
| **M1-16** | Docs: `docs/ARCHITECTURE.md`, `docs/SECURITY.md`, `docs/RUNBOOK.md`, README quick start; PRD §15 items 20 and 21 marked resolved. | — | 1d | Reviewed in PR. |
| | **Total** | | **≈ 21d** | |

**Sequencing:** 01 → 02 → 03 → (04, 06) → 05 → 07 → 08 → 09 → 10 → 11 → 12 → 13 → 14 → 15 → 16. CI (15) is introduced as a skeleton right after 03 and grows with each task.

**Commits:** Conventional Commits, one logical change each, authored and committed only as `Yazeed Hamad Alharthi <yazed.501k@gmail.com>`, no AI attribution. One PR for M1 from `feat/m1-foundation`.

---

## 4. M2–M4 outline (for sequencing only)

| Milestone | Core deliverables | Depends on |
|---|---|---|
| **M2 Intelligence** | LLM provider interface + prompt registry; A1 extraction with verbatim-span check; A2 hybrid retrieval (pgvector + filters) and CDI query; A3 YAML rules engine with versioned policies; recorded-response fixtures; eval runner and CI gates | M1-04, 08, 11 |
| **M3 Readiness** | A5 scoring service on live findings; per-point explanations; what-if simulator; prioritised work queue; evidence viewer with span highlight | M2 |
| **M4 Interop** | FHIR `Claim(preauthorization)` builder; HL7 Validator (Java) wrapper with stored reports; labelled simulated payer; minimal A6 with faithfulness check; Playwright E2E for the full flow | M3 |

---

## 5. Risks

| Risk | Impact | Mitigation |
|---|---|---|
| **Restructure breaks the existing UI** | Medium | M1-01 is a pure move with a build check before any other change. |
| **RLS mistakes leak data across organisations** | High | App connects as a non-owner role; RLS tests are mandatory in CI; no `BYPASSRLS`. |
| **Synthetic data is too easy, so evals overstate quality** | High | Adversarial scenarios (contradictions, Arabic-only, injection, near-miss durations) are required; annotations by construction plus a 10-case manual review. |
| **Audit chain race conditions** | Medium | Row-level lock on the case's chain head; concurrency test. |
| **Scope creep into M2 during M1** | Medium | M1 ships no AI behaviour changes; existing Gemini endpoints are ported as-is behind the new API. |
| **Authoring environment cannot install packages** (see §7) | High | Verification runs on GitHub Actions; each PR reports CI results, not local claims. |

---

## 6. TODO(verify) — facts that must come from an authoritative source

| # | Item | Why it matters | Needed by |
|---|---|---|---|
| V1 | NPHIES Implementation Guide: canonical profile URLs and a downloadable FHIR package for prior-authorization `Claim` and `ClaimResponse` | Real validation in M4 | M4 |
| V2 | NPHIES code systems and URIs for diagnoses (ICD-10-AM), services (SBS), and adjudication / denial reasons | Replace demo code systems | M2 |
| V3 | The ICD-10-AM code and the SBS code for "MRI lumbar spine without contrast" | MVP scenario coding | M2 |
| V4 | Payer appeal / reconsideration deadlines applicable in KSA (CHI rules or contract-specific) | Deadline tracking (FR-A6-05) | M4 |
| V5 | PDPL and implementing-regulation requirements for processing health data with a third-party LLM provider, including cross-border transfer | LLM provider choice and de-identification design | M2 |
| V6 | NCA control set applicable to a SaaS processing health data (ECC, CCC) | Security baseline | Before pilot |
| V7 | Whether any public payer policy text may be used for RAG, or whether policies must be authored as demo text | Policy corpus in M2 | M2 |

Until verified, all of the above stay as clearly labelled demo values.

---

## 7. Environment constraint (stated up front)

The environment used to author this plan **cannot install packages**: the PyPI and npm registries are blocked. FastAPI, SQLAlchemy, Alembic and the frontend dependencies are not available locally, and container images may not be pullable.

Consequences:
- Code can be written and pushed here, but **tests, builds and `docker compose` must run on GitHub Actions**, which has normal network access.
- Every PR will state which checks ran in CI and their results. Nothing is reported as "working" unless CI shows it.
- If faster iteration is wanted, the alternative is to run the work from an environment with registry access (e.g. local machine with Claude Code, or Codespaces).

---

## 8. Decisions needed before coding

| # | Question | Recommendation |
|---|---|---|
| D1 | Move the backend from Express/TypeScript to **Python/FastAPI** as the PRD states? | **Yes.** The Python ecosystem is stronger for RAG, evals and FHIR tooling, and it matches your MIJHAR stack. |
| D2 | Restructure into `frontend/` + `backend/` monorepo (large diff, file moves)? | **Yes**, done as a single isolated commit. |
| D3 | Remove the Express server entirely in M1, or keep it temporarily as a proxy? | **Remove** once the frontend is wired (M1-13), to avoid two APIs. |
| D4 | Auth for the MVP: built-in dev IdP only, or integrate a real IdP now (Keycloak, Auth0, Azure AD)? | **Dev IdP now**, OIDC-ready; real IdP chosen at pilot. |
| D5 | Production LLM: keep Gemini, or abstract now for an in-Kingdom or self-hosted model later? | **Abstract now, Gemini as default.** Final choice after V5. |
| D6 | Deployment target beyond docker-compose (Cloud Run, a Saudi cloud region, none yet)? | **None in M1.** Decide before the pilot. |
| D7 | Execution venue: continue from this environment (CI-verified, slower loop) or from a machine with registry access? | Either works; a machine with registry access is faster. |

**Next step:** approve or amend D1–D7. On approval, work starts on `feat/m1-foundation` with M1-01.
