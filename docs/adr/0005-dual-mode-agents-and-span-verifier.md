# ADR 0005 — Dual-mode agents and the span verifier

- **Status:** Accepted (2026-10-30)

## Context
M2 replaces the demo behaviour with agents A1 (clinical understanding), A2 (evidence hunter) and A3 (policy reasoning). Two constraints shape the design:

1. **No evidence, no claim.** A fact that cannot be pointed to in the patient record must never reach a reviewer, a score or a payer.
2. **CI must be deterministic and free**, and live model calls are not available from every environment that builds the project.

## Decision
- **Two execution modes with one output type.** A deterministic baseline (Arabic/English cue lists and a number parser) and an LLM extractor behind a `Provider` interface (`GeminiProvider`, `ReplayProvider`) both return `Fact` objects and pass through the same verifier, rules engine and scoring.
- **The model supplies quotes, never offsets or numbers.** `app/agents/verify.locate()` finds each quote in the source document (exact match first, then a normalised match that folds Arabic diacritics, tatweel and alef/ya/ta-marbuta variants and maps back to original offsets). A quote that is not found is **rejected and counted**. Week and session counts are parsed by our own parser from the verified text.
- **Outcomes are decided by code.** A2 classifies FOUND / PARTIAL / MISSING from verified facts; A3 evaluates versioned YAML policy rules (`app/rules/policies/`). The model cannot set a status, a rule outcome or a score.
- **Failure is labelled, not hidden.** If the provider fails, the pipeline runs the baseline and records `fallback_reason` on the analysis run, the audit entry and the UI. The eval runner counts fallbacks in LLM mode and gates them at zero, so a missing fixture can never pass as an LLM score.
- **Prompts are versioned files** (`app/prompts/*.md`) registered in the `prompts` table with their SHA-256; replay fixtures are keyed by prompt hash plus inputs.
- **Prompt injection** inside clinical text is treated as data: the prompt delimits the document and tells the model to ignore instructions in it, a detector flags instruction-like passages for reviewers, and the eval suite checks that removing the injected text does not change any outcome.

## Consequences
- Every stored fact links to an `evidence_spans` row whose text equals the document substring; an integration test checks this for all facts.
- The baseline is a floor and a regression lock, not a claim of clinical quality: it is tuned to the synthetic templates. The LLM path is measured separately in the `live-evals` workflow, and replayed in CI once fixtures are recorded.
- Adding a payer or a service means adding a YAML policy and eval cases, not changing code, as long as the existing predicates suffice.
