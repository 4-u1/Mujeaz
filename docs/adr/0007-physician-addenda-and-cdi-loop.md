# ADR 0007 — Physician addenda and the documentation-query loop

- **Status:** Accepted (2026-10-30, M3 decisions D1, D2 and D5)

## Context
Most avoidable prior-authorization denials in the MRI scenario are documentation gaps: the therapy happened, but the request does not prove it. M2 detects the gap and writes a question for the physician. M3 must let the physician answer it without turning that answer into a way of documenting care that never happened.

## Decision
- **Queries are tracked tasks.** Each requirement that A2 marks PARTIAL or MISSING opens a `documentation_queries` row (`OPEN → ANSWERED | DECLINED | WITHDRAWN`). Queries are idempotent across re-analyses and are withdrawn when the requirement becomes satisfied from other evidence.
- **Answers are structured, never free text.** Therapy: start date, end date, sessions, provider, optional NSAID. Red flag: one of a fixed list of findings with an observation date. The server validates the answer against the case:
  - no future dates;
  - therapy must have **ended on or before the request date** — an addendum documents care that already happened; a later course needs a new request.
- **One renderer.** The server turns the answer into a bilingual addendum from a fixed template (`app/cdi/addendum.py`). The same renderer feeds the what-if simulator, so a simulation and the real re-analysis cannot diverge (integration test: equal for every fixable case).
- **The addendum is a document, not a shortcut.** It is stored in `clinical_documents` (`doc_type = 'addendum'`, author, signed-at, query id) and goes through A1 and the span verifier like any other note. Facts from it are labelled *post-request addendum* in the evidence list, the document viewer and the explanation.
- **Payers decide.** `addenda.accepts_post_request` in the policy YAML: Demo Payer A accepts addenda, Demo Payer B does not. When a payer does not accept them, the addendum is shown but excluded from evidence, and the reason says so.
- **Re-analysis is automatic** in the same transaction as the answer (D5), with audit entries for the answer and the analysis. The human submission gate is unchanged.

## Consequences
- The loop is measured: the eval suite checks that a sufficient answer resolves the requirement, an insufficient one does not, recorded non-attendance still blocks, and a payer that refuses addenda changes nothing. The expected acceptance comes from the policy text, not the YAML flag, so a wrong flag fails the gate (checked by mutation).
- The template guarantees extraction; it does not test how real physicians write. Free-text addenda would need the LLM path and clinician-written evaluation cases.
