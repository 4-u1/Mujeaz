# Mujeaz — Security

> Scope: milestone M1, synthetic data only. This is not a statement of regulatory compliance. PDPL, CHI and NCA requirements are tracked as `TODO(verify)` items V5–V6 in `docs/IMPLEMENTATION_PLAN.md`.

## Controls in place

| Area | Control | Where |
|---|---|---|
| Authentication | RS256 JWT with `iss`, `aud`, `exp`, `iat`, `sub` required | `app/security/jwt.py` |
| | Dev identity provider only when `MUJEAZ_DEV_AUTH=true`; startup refuses it with `MUJEAZ_ENV=production` | `app/config.py` |
| | OIDC-ready: `MUJEAZ_JWKS_URL` switches verification to an external IdP | ADR 0003 |
| Authorisation | Role → permission matrix; every route declares its permission; full matrix test | `app/security/rbac.py` |
| | Human gates (submission, appeal) require specific permissions and are recorded | `app/cases/state_machine.py` |
| Tenant isolation | PostgreSQL RLS on all tenant tables; app connects as non-owner `mujeaz_app` without `BYPASSRLS` | migration `0001` |
| | Tested both through the API and directly in SQL | `tests/integration/test_api.py` |
| Audit | Append-only (grants + trigger), SHA-256 hash chain, server-side verify, tamper test | ADR 0004 |
| Input handling | Pydantic schemas, size limits (note ≤ 20,000 chars), 422 error envelope | routers |
| Rate limiting | 20 AI requests/min per user (in-process) | `app/ai/router.py` |
| LLM safety | Clinical text inside delimiters and treated as data; whitelisted appeal fields; no patient name or ID sent to the model | `app/ai/service.py` |
| | Labelled fallback contains no clinical facts | |
| Errors | Generic messages; internal details only in server logs with a request id | `app/main.py` |
| Transport & headers | nginx adds `nosniff`, `DENY` framing, `no-referrer` | `infra/nginx/default.conf` |
| Containers | Non-root users | Dockerfiles |
| Secrets | From environment only; `.env*` git-ignored | `.env.example` |
| Supply chain | `pip-audit` and `npm audit` in CI (report-only for now) | `.github/workflows/ci.yml` |

## Known gaps (tracked)

- TLS termination is expected in front of nginx; not configured in the local stack.
- The in-process rate limiter does not span replicas.
- The dev signing key is ephemeral unless `MUJEAZ_JWT_PRIVATE_KEY_PEM` is set.
- A database superuser can still alter audit rows; this is **detected**, not prevented. External anchoring of chain heads is a future step.
- De-identification before LLM calls is limited to field whitelisting; full de-identification is planned with V5.

## Reporting

Report security issues privately to the repository owner, not in public issues.
