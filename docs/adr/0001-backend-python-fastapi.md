# ADR 0001 — Backend in Python with FastAPI

- **Status:** Accepted (2026-10-30)
- **Deciders:** Yazeed Hamad Alharthi

## Context
The prototype served two LLM endpoints from Express/TypeScript. The PRD target (§9) needs retrieval (pgvector), a rules engine, an evaluation harness, FHIR validation tooling and typed, testable agents. The author's other agent system (MIJHAR) is Python/LangGraph.

## Decision
Build the backend as a Python 3.12 FastAPI service (`backend/`) with Pydantic v2, SQLAlchemy 2 and Alembic. The React frontend stays in TypeScript. Scoring remains specified once in `shared/scoring.ts` and is ported to Python with shared test vectors that both implementations must pass.

## Consequences
- Two languages in the repo; parity is enforced by `shared/scoring_vectors.json` tests on both sides.
- Strong ecosystem for RAG, evals and FHIR; typed request/response models generate OpenAPI for the frontend.
- The Express server is removed once the frontend uses the new API.
