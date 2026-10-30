# Mujeaz — Implementation Plan: M2 Intelligence

| | |
|---|---|
| Scope | **M2 — Intelligence**: agents A1, A2, A3 on the MRI Lumbar Spine scenario, with an evaluation suite gating CI |
| Baseline | `feat/m1-foundation` (PR #2, all checks green). M2 starts after PR #2 is merged into `main`. |
| Author | Yazeed Hamad Alharthi |
| Status | **Approved 2026-10-30. D1–D5 as recommended (D1: the `GEMINI_API_KEY` secret is added by the owner; until then only the baseline is evaluated). PR #2 merged.** |

---

## 1. Objective

Replace the demo behaviour with real agents. For any of the 50 synthetic cases, a single "Analyze" action must:

1. **A1** extract clinical facts from every document in the patient record, each tied to a verbatim span;
2. **A2** find evidence for each policy requirement across the **whole** record, classify it FOUND / PARTIAL / MISSING, and produce a physician documentation query (CDI) when it is missing;
3. **A3** evaluate the payer rules **deterministically** from structured facts;
4. **A5** (already deterministic) compute the Readiness Score and revenue risk from those results;

and persist everything with agent-run telemetry and audit entries — while the eval suite proves quality against the ground truth.

**Exit criteria**

- All M2 eval gates in §5 pass in CI.
- `POST /api/cases/{id}/analyze` runs the pipeline end to end for any synthetic case, writes facts, evidence, requirements, scores and `agent_runs`, transitions the case to `RISK_DETECTED` or `DECISION_READY`, and appends audit entries.
- The UI triggers analysis and shows progress, results and the CDI question.
- No fact is stored without a verified span. Prompt-injection cases do not change outcomes.

---

## 2. Design

### 2.1 Two execution modes per agent

| Mode | What it is | Used for |
|---|---|---|
| **Deterministic baseline** | Rules + Arabic/English pattern extraction, no model | CI gates, fallback when the model is unavailable, a floor the LLM must beat |
| **LLM** (Gemini by default) | Structured-output extraction through a provider interface | Production path; evaluated in a live workflow |

Both modes produce the same typed output and pass through the same verifier. The orchestrator records which mode ran.

**Why both:** CI must be deterministic and free, and I cannot run live models from my environment. The baseline also exposes over-fitting: if the LLM does not clearly beat a pattern matcher on held-out data, the evaluation set is too easy.

### 2.2 The verifier (non-negotiable rule 1)

The model never supplies offsets. It returns a **quote**; the verifier locates the quote in the source document (exact, then whitespace/diacritic-normalised match) and computes `char_start/char_end` itself. If the quote is not found, the fact is **rejected and counted** as a hallucination in telemetry. Only verified facts are stored, linked to `evidence_spans`.

### 2.3 Retrieval (A2)

- New table `document_chunks` (sentence-level chunks with offsets) with a PostgreSQL `tsvector` using the built-in **`arabic`** and **`english`** text-search configurations (verified available in PostgreSQL 16) and an optional `vector(768)` column.
- **M2 gate runs on full-text + structured filters** (date window, document type). Embeddings are behind a flag and evaluated only in the live workflow (decision D2).
- Requirement queries are bilingual and versioned with the policy.

### 2.4 Rules engine (A3)

- Policy rules live as versioned YAML (`backend/app/rules/policies/*.yaml`) with the source text they cite; the seeder loads them into `policy_versions` / `policy_rules`.
- The engine evaluates typed predicates over structured facts: `min_duration_weeks`, `min_sessions`, `exempt_if_any`, `diagnosis_prefix_in`, `contradiction_blocks`.
- Every evaluation stores the policy version and the facts that decided it. Unit tests cover every predicate and edge (e.g. 5.9 vs 6 weeks).

### 2.5 LLM layer

- `Provider` interface: `generate(prompt_id, version, inputs, schema) → output, usage`. Implementations: `GeminiProvider`, `ReplayProvider` (recorded responses keyed by `sha256(prompt_version + inputs)`).
- **Prompt registry:** prompts are versioned files in `backend/app/prompts/`; their hashes are registered in the `prompts` table at bootstrap; every `agent_run` records model, prompt version, input hash, latency, tokens and cost.
- Untrusted clinical text stays inside delimiters; an injection detector flags suspicious instructions and records them, but outcomes are decided by the verifier and rules engine, never by the model's instructions.

### 2.6 Orchestration

An explicit pipeline (no hidden autonomy) in `backend/app/orchestrator/`: `A1 → verify → A2 → A3 → A5 → persist → transition → audit`, one database transaction per analysis, idempotent re-runs (a new analysis supersedes the previous one; history is kept). Progress is streamed with Server-Sent Events.

---

## 3. Work breakdown — M2

| ID | Task | PRD refs | Est. | Done when |
|---|---|---|---:|---|
| **M2-01** | Migration `0002`: `document_chunks` (tsvector ar/en, optional vector), `clinical_facts.value jsonb` (structured fields), `analysis_runs` (groups agent runs), links facts/evidence → `evidence_spans` | §10, FR-A1-02 | 1d | up/down tested |
| **M2-02** | Chunker + indexer for clinical documents (sentence split ar/en, offsets preserved) | FR-A2-04 | 1d | Every chunk maps back to exact offsets |
| **M2-03** | Span verifier (exact → normalised match; Arabic diacritics/tatweel/alef variants) | FR-A1-02/04 | 1d | Property tests: never stores a span that differs from the source |
| **M2-04** | Provider interface, Gemini provider, Replay provider, prompt registry, telemetry | §13 | 1.5d | Unit tests with a fake provider |
| **M2-05** | **A1** baseline extractor (symptom duration, exam, therapy sessions/weeks, medications, red flags, claims of therapy) + LLM extractor with the same schema | FR-A1-01..04 | 3d | Baseline passes A1 gates on the dev split |
| **M2-06** | **A2** hybrid retrieval + FOUND/PARTIAL/MISSING classifier + contradiction handling + bilingual CDI question | FR-A2-01..05 | 3d | A2 gates on the dev split |
| **M2-07** | **A3** YAML rules engine + Demo Payer A lumbar policy v2026.1 + loader | FR-A3-01..04 | 2d | 100% agreement on dev split; predicate unit tests |
| **M2-08** | Orchestrator, `POST /api/cases/{id}/analyze`, SSE progress, persistence, transitions, audit | FR-HR-02, FR-AU-02 | 2d | Integration tests for all 8 scenarios |
| **M2-09** | Dataset v2: **held-out split** generated from a separate set of paraphrase templates not used while writing the baseline; adversarial variants (negations, typos, Arabic-Indic digits, dates as text) | §13 | 2d | 30 extra held-out cases; manifest records the split |
| **M2-10** | Eval runner `evals/run.py`: metrics, per-scenario breakdown, JSON + Markdown report, gate check | §13 | 1.5d | Report attached to CI summary |
| **M2-11** | CI: offline gates on dev + held-out (baseline and replayed LLM fixtures); separate `live-evals` workflow (manual/nightly) that runs Gemini and can record fixtures | §6 | 1d | Green CI; live workflow documented |
| **M2-12** | UI: Analyze button, progress, facts with source, evidence status per requirement, CDI question, mode badge (baseline/LLM) | §7 | 2d | Playwright: analyze a case → readiness appears |
| **M2-13** | Docs: ADR 0005 (dual-mode agents & verifier), ADR 0006 (retrieval), EVALS update, PRD §15 | — | 0.5d | Reviewed in PR |
| | **Total** | | **≈ 21.5d** | |

Sequencing: 01 → 02 → 03 → 04 → 05 → 07 → 06 → 08 → 09 → 10 → 11 → 12 → 13. Held-out data (09) is generated **before** baseline tuning on it is possible — the baseline is written against the dev split only.

---

## 4. Evaluation design

| Split | Cases | Use |
|---|---:|---|
| **dev** | 50 (current dataset) | Building and tuning |
| **held-out** | 30 (new, separate paraphrase templates) | Gates only; never inspected while writing rules or prompts |

Ground truth comes from construction (exact spans, expected statuses and rule outcomes). Metrics are reported per scenario and per language.

## 5. Gates (CI)

| Metric | Gate | Applies to |
|---|---|---|
| A1 fact precision / recall | ≥ 0.90 / ≥ 0.85 | dev and held-out |
| Facts stored without a verified span | **0** | all |
| A2 evidence classification accuracy | ≥ 0.90 | dev and held-out |
| A2 retrieval Recall@5 | ≥ 0.90 | dev and held-out |
| A3 rule-outcome agreement | ≥ 0.95 | dev and held-out |
| Prompt-injection cases with unchanged outcome | **100%** | all |
| Scoring parity | 100% | (already in CI) |

If the deterministic baseline scores near 100% on held-out data, I will report that the dataset is too easy rather than claim success, and harden it.

---

## 6. Risks

| Risk | Impact | Mitigation |
|---|---|---|
| **Synthetic data is template-like**, so scores overstate real-world quality | High | Separate held-out templates, adversarial variants, baseline-vs-LLM comparison, honest reporting; real clinician-written cases before any pilot |
| Arabic extraction quality (morphology, digits, dialect) | Medium | Normalisation in the verifier; Arabic-only held-out cases; per-language metrics |
| No live model access from my environment | Medium | CI uses baseline + replayed fixtures; live workflow runs on GitHub with your API key |
| LLM cost and latency | Low (synthetic scale) | Telemetry per run; caching by input hash |
| Scope creep into M3 (what-if, evidence viewer UI) | Medium | M2 UI shows results only; richer UX is M3 |

---

## 7. Decisions needed

| # | Question | Recommendation |
|---|---|---|
| **D1** | Add a `GEMINI_API_KEY` **GitHub Actions secret** so the live-eval workflow can run the LLM path and record fixtures? | **Yes.** Without it, only the baseline is evaluated, and the LLM path stays unmeasured. |
| **D2** | Embeddings in M2: full-text only, Gemini embeddings, or a local multilingual model? | **Full-text (Arabic + English) for the CI gate; Gemini embeddings behind a flag, measured in the live workflow.** |
| **D3** | Agent framework: plain Python pipeline or LangGraph (as in MIJHAR)? | **Plain Python pipeline.** The flow is linear and already governed by the state machine; LangGraph adds a dependency without changing behaviour. |
| **D4** | Held-out cases: generated only by me, or 10 of them written or reviewed by someone with clinical background? | **Both.** I generate 30; if you can get 10 reviewed by a clinician or a revenue-cycle specialist, that is the strongest credibility signal for a pilot. |
| **D5** | Merge PR #2 before M2 starts? | **Yes.** M2 branches from `main` after the merge. |

**Next step:** approve or amend D1–D5. On approval, work starts on `feat/m2-intelligence` with M2-01.
