# ADR 0006 — Retrieval for the evidence hunter (A2)

- **Status:** Accepted (2026-10-30)

## Context
A2 must search the **whole** patient record — not only the ordering note — for proof of each policy requirement, in Arabic, English and mixed notes. Decision D2 of the M2 plan chose full-text retrieval for the CI gate and deferred embeddings to the live workflow.

## Decision
- Documents are split into sentence chunks with exact character offsets (`app/nlp/chunker.py`); chunk boundaries avoid decimal points.
- **Ranking in M2 is BM25 in Python** over normalised, lightly stemmed Arabic/English tokens (`app/agents/a2_evidence.bm25_rank`). The same function runs in the API and in `evals/run.py`, so the Recall@5 measured in CI is the recall the product has.
- The database stores the same chunks in `document_chunks` with a generated `tsvector` (`to_tsvector('arabic', …) || to_tsvector('english', …)`, GIN index) and an optional `vector(768)` column. Chunks are written at seed time and on every analysis (idempotent).
- Requirement queries are bilingual and versioned inside the policy YAML.
- Classification does not depend on rank: the status comes from verified facts, and retrieval supplies the top-k passages shown to reviewers and, in LLM mode, the context window.

## Consequences
- Retrieval quality is measured, not assumed: Recall@5 is gated at ≥ 0.90 on both splits.
- The PostgreSQL full-text index is in place for record sizes where in-process BM25 stops being cheap; switching the ranker is a change behind one function, measured by the same eval.
- Embeddings (Gemini or a local multilingual model) are a later, measured addition, not a default.
