# Mujeaz — Runbook

## Run the full stack

```bash
cp .env.example .env            # optional: add GEMINI_API_KEY
docker compose -f infra/docker-compose.yml up --build
```

| Service | URL |
|---|---|
| Web app | http://localhost:8080 |
| API docs (OpenAPI) | http://localhost:8000/docs |
| Health / readiness | http://localhost:8000/healthz · /readyz |
| PostgreSQL | localhost:5432 (`postgres` / `$POSTGRES_PASSWORD`) |

The `migrate` service runs `python -m app.cli bootstrap` once: migrations, application-role password, seed data. It is idempotent.

**Demo users** (development sign-in): `dr.khalid` (physician), `sara.auth` (authorization officer), `omar.coder` (coder), `lama.appeals` (appeals officer), `faisal.rcm` (RCM manager), `noura.audit` (auditor).

## Run services locally without Docker

```bash
# database
docker run -d --name mujeaz-db -e POSTGRES_PASSWORD=postgres -e POSTGRES_DB=mujeaz -p 5432:5432 pgvector/pgvector:pg16

# backend
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
python -m app.cli bootstrap
uvicorn app.main:app --reload --port 8000

# frontend (proxies /api to :8000)
cd ../frontend && npm install && npm run dev   # http://localhost:5173
```

## Tests

```bash
cd backend
pytest -q                                   # unit tests only
MUJEAZ_RUN_INTEGRATION=1 pytest -q          # + integration (needs the database above)

cd ../frontend && npx vitest run && npx tsc --noEmit
python -m evals.generator.generate --check  # from the repo root
```

## Common operations

| Task | Command |
|---|---|
| Reset demo data | `python -m app.cli seed --reset` |
| Regenerate synthetic dataset | `python -m evals.generator.generate` (commit the result) |
| Regenerate scoring vectors | `node --experimental-strip-types shared/generate-scoring-vectors.ts` |
| New migration | `cd backend && alembic revision -m "..."` (hand-written SQL; use `exec_driver_sql`) |
| Verify a case's audit chain | `GET /api/audit/{case_id}/verify` as `noura.audit` |

## Troubleshooting

| Symptom | Likely cause |
|---|---|
| `401` after restarting the backend | Ephemeral dev signing key; sign in again or set `MUJEAZ_JWT_PRIVATE_KEY_PEM` |
| Empty case list | Signed in as `other.auth` (isolation-test organisation), or seed not run |
| `/readyz` 503 | Database unreachable or `mujeaz_app` password mismatch (`MUJEAZ_APP_DB_PASSWORD`) |
| AI responses say “fallback” | `GEMINI_API_KEY` not set or the provider call failed (see backend logs by request id) |
