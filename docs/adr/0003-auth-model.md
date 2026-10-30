# ADR 0003 — Authentication and authorisation

- **Status:** Accepted (2026-10-30)

## Context
Every action must be attributable to a person with a role (PRD FR-HR-01, §12). A real identity provider is not chosen yet.

## Decision
- **Tokens:** RS256 JWTs carrying `sub`, `org_id`, `roles`, `iss`, `aud`, `exp`.
- **MVP issuer:** a built-in development identity provider (`POST /api/auth/dev-login`, enabled only when `MUJEAZ_DEV_AUTH=true`) that signs with a local RSA key and publishes it at `/.well-known/jwks.json`.
- **OIDC-ready:** verification accepts any issuer configured through `MUJEAZ_JWT_ISSUER`, `MUJEAZ_JWT_AUDIENCE` and `MUJEAZ_JWKS_URL`, so a real IdP (Keycloak, Entra ID, Auth0, a national IdP) replaces the dev issuer by configuration.
- **Authorisation:** role → permission matrix in code (`backend/app/security/rbac.py`), enforced per endpoint, covered by a full matrix test.
- **Tenant isolation:** PostgreSQL Row-Level Security keyed on `app.org_id`, set per transaction from the token. The application connects as a non-owner role without `BYPASSRLS`.

## Consequences
- The dev issuer must never be enabled in production; startup refuses `MUJEAZ_DEV_AUTH=true` when `MUJEAZ_ENV=production`.
- Isolation does not depend only on application code.
