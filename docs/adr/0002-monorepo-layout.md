# ADR 0002 — Monorepo layout

- **Status:** Accepted (2026-10-30)

## Decision
```
frontend/   React 19 + Vite web app
backend/    FastAPI service, migrations, tests
shared/     language-neutral specs (scoring vectors) + the TS scoring reference
evals/      synthetic data generator, golden dataset, eval runners
infra/      docker-compose and container config
docs/       PRD, ADRs, architecture, security, runbook
```
One repository keeps the API contract, the scoring spec and the evaluation data versioned together, and lets one CI pipeline verify them.

## Consequences
- Each part has its own toolchain (`uv`/pip for backend, npm for frontend).
- The move of the web app was done as an isolated rename-only commit to keep history readable.
