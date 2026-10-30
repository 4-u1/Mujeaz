# Mujeaz — Implementation Plan: M3 Readiness

| | |
|---|---|
| Scope | **M3 — Readiness**: close the loop before submission — explain the score, simulate fixes, route the physician documentation query, re-analyse |
| Baseline | `main` @ `9ac2a5a` (M2 merged, all checks green) |
| Author | Yazeed Hamad Alharthi |
| Status | **Draft — awaiting approval. No code written yet.** |

---

## 1. Objective

M2 tells the team *that* a request will probably be denied. M3 must let them **fix it before it is sent**:

1. **Explain** every point the request loses, tied to the rule and the evidence (or its absence) that caused it.
2. **Simulate** what a fix would change ("if 6 weeks of therapy were documented, readiness 51 → 100").
3. **Ask** the physician the documentation question as a tracked task, collect a structured answer, and store it as a signed addendum.
4. **Re-analyse** automatically, so the case moves from `RISK_DETECTED` to `DECISION_READY` with the new evidence cited.
5. **Prioritise** the authorization officer's work by revenue at risk and age.

**Exit criteria**

- End to end in the UI (Playwright): officer analyses → risk detected → physician answers the query → automatic re-analysis → `DECISION_READY` → officer approves the submission gate. Every step is in the audit chain.
- For every synthetic case where a fix is possible, the what-if prediction equals the result of the real re-analysis after the addendum (eval gate, 100%).
- Every readiness score is fully explained: the per-component contributions reproduce the overall score exactly, including gates.
- A second payer policy works with **no code changes** — only YAML and eval cases.

---

## 2. Design

### 2.1 Readiness explanation

`A5` already computes six weighted components and two gates with deterministic formulas (`shared/scoring.ts`, Python port, parity-tested). M3 adds an **explanation** built from the same numbers:

- per component: score, weight, weighted contribution, points lost, and the cause (rule code, requirement, fact or missing fact);
- the gate, if any, and how many points it removed;
- an invariant checked in tests: `Σ contributions − gate reduction = overall` for every case.

The decision threshold (currently `90`, hard-coded in the pipeline) moves into the policy YAML as `decision_ready_min`. The scoring formulas themselves do not change, so TypeScript parity vectors stay valid.

### 2.2 What-if simulator

`POST /api/cases/{id}/what-if` runs the **pure pipeline** (`orchestrator/core.analyze`) on the stored record plus a hypothetical document, and returns the before/after delta. Nothing is persisted.

- Hypotheses are limited to what the policy can use: the requirement's fact (e.g. *conservative therapy: N weeks, M sessions*) or a red-flag exemption. No free text.
- The hypothetical document is rendered from the same template as a real addendum (§2.3), so the simulator and the real flow cannot drift. This is what makes the "prediction = reality" gate meaningful.
- Responses are labelled `simulation` in the API and the UI.

### 2.3 Physician documentation query (CDI) loop

New table `documentation_queries`: case, requirement, question (en/ar), status `OPEN → ANSWERED | DECLINED | WITHDRAWN`, assignee role, created/answered by, due date.

- Created automatically for each requirement A2 marks PARTIAL or MISSING (idempotent across re-analyses; withdrawn when the requirement is met).
- The physician (`case:document`) answers with a **structured form** — therapy type, start and end dates, number of sessions, provider — or declines with a reason.
- The server renders the answer into an **addendum** (`clinical_documents`, `doc_type = 'addendum'`, author, signed-at, linked query), with a fixed bilingual template. A1 extracts from it like any other document, so the "verified span" rule is unchanged.
- Saving an addendum triggers re-analysis in the same transaction and writes audit entries for the answer and the analysis.
- **Addenda are labelled as post-request documentation** everywhere they are cited (evidence list, explanation, future FHIR attachment). Whether a payer accepts them is a policy setting: `accepts_post_request_addenda` (see D1).

### 2.4 Work queue

`GET /api/queue` returns the cases needing action with a transparent priority:

`priority = revenue_at_risk × (1 + 0.1 × days_since_request)`, capped, with the formula shown in the UI. Filters: status, payer, open queries, assignee role. Physicians see their open queries; officers see cases.

### 2.5 Evidence viewer

A document panel that opens on any fact or evidence item, with the span highlighted and the top-5 retrieved passages per requirement listed.

**Offsets:** Python counts code points; JavaScript strings index UTF-16 code units. Arabic is in the BMP, so they agree today, but a single emoji or rare symbol would shift every highlight after it. The API will return offsets in **both** units (`charStart` and `utf16Start`), with a test on text containing astral-plane characters.

### 2.6 Second policy (configuration, not code)

Add **Demo Payer B — Lumbar MRI v2026.1** with different terms: *≥ 8 weeks of therapy OR ≥ 6 completed sessions*, and does not accept post-request addenda. This needs two new predicates (`min_sessions`, `any_of`) — the last engine change; after that a new policy should be YAML only. Twenty new synthetic cases assigned to DPB, generated the same way as the existing ones.

---

## 3. Work breakdown — M3

| ID | Task | PRD refs | Est. | Done when |
|---|---|---|---:|---|
| **M3-01** | `decision_ready_min` and `accepts_post_request_addenda` in policy YAML; pipeline reads them | §8 | 0.5d | Unit tests; no change to scoring vectors |
| **M3-02** | Readiness explanation (contributions, causes, gate); API + twin | §8, FR-A5 | 1.5d | Invariant test passes on all 100 cases |
| **M3-03** | Addendum template (en/ar) + renderer, shared by what-if and the real flow | FR-CDI | 0.5d | Round-trip test: rendered addendum → A1 → expected facts |
| **M3-04** | What-if endpoint (hypotheses validated against the policy, no persistence) | FR-A5-04 | 1d | Integration tests; read-only verified |
| **M3-05** | Migration `0003`: `documentation_queries`; addendum columns on `clinical_documents` (author, signed_at, query_id); RLS | §10 | 0.5d | up/down tested |
| **M3-06** | CDI loop: create/withdraw queries on analysis; answer/decline endpoints; addendum → re-analysis → audit | FR-CDI | 2d | Integration tests for answer, decline, permission, re-analysis |
| **M3-07** | Rules engine: `min_sessions`, `any_of`; Demo Payer B policy; 20 DPB synthetic cases + annotations | FR-A3 | 1.5d | Eval gates pass for DPB; no code change needed for the policy itself |
| **M3-08** | Work queue endpoint with the stated priority formula | §7 | 0.5d | Ordering tests |
| **M3-09** | Evidence viewer API: offsets in code points and UTF-16; retrieved passages per requirement | FR-A2-05 | 0.5d | Astral-plane test |
| **M3-10** | UI: work queue, readiness explanation, what-if panel, physician query inbox + answer form, document viewer with highlights | §7 | 3d | Vitest for offset mapping and form validation |
| **M3-11** | Evals: what-if = reality gate; CDI-loop scenario per case; explanation invariant; DPB split | §13 | 1d | New gates green in CI |
| **M3-12** | Playwright: full loop from analysis to the submission gate across two roles | — | 1d | Green in the stack job |
| **M3-13** | Housekeeping from the M2 review: remove orphaned `evidence_spans` on re-analysis; decision threshold out of code | — | 0.5d | Tests |
| **M3-14** | Docs: ADR 0007 (addenda and the CDI loop), EVALS, ARCHITECTURE, PRD §15, README | — | 0.5d | Reviewed in PR |
| | **Total** | | **≈ 15d** | |

Sequencing: 01 → 02 → 03 → 04 → 05 → 06 → 07 → 08 → 09 → 11 → 10 → 12 → 13 → 14.

---

## 4. Evaluation additions

| Metric | Gate | Applies to |
|---|---|---|
| What-if prediction equals re-analysis after the matching addendum | **100%** | every fixable case, all splits |
| Explanation reproduces the overall score | **100%** | all cases |
| CDI loop resolves fixable cases (PARTIAL/MISSING → FOUND after a sufficient answer) | **100%** | dev, held-out, DPB |
| Insufficient answers do **not** resolve the requirement (e.g. 4 weeks for a 6-week rule) | **100%** | same |
| Existing M2 gates (A1, A2, A3, injection) | unchanged | dev, held-out, **DPB** |

The same caveat applies: the addendum is generated from our own template, so these gates prove the loop is consistent, not that real physician free text is understood. That is what the live LLM workflow and clinician-written cases measure.

---

## 5. Risks

| Risk | Impact | Mitigation |
|---|---|---|
| **Addenda as a path to documentation that was never done** | High (compliance) | Structured answer with dates and provider; addendum labelled post-request everywhere; payer setting decides if it counts; physician identity and timestamp in the audit chain; human gate before submission is unchanged |
| What-if and real flow diverge | Medium | One renderer for both; equality gate in CI |
| Score explanations that do not add up | Medium | Invariant test on every case |
| UTF-16 vs code-point offsets | Medium | Both returned; astral-plane test |
| Scope creep into FHIR (M4) and appeals (M5) | Medium | Addendum is stored as a document only; FHIR attachment comes in M4 |

---

## 6. Decisions needed

| # | Question | Recommendation |
|---|---|---|
| **D1** | Can a physician addendum written **after** the request count as evidence? | **Yes, but only as a structured answer** (dates, sessions, provider), labelled "post-request addendum" everywhere, and per payer: Demo Payer A accepts, Demo Payer B does not. Free-text addenda are out of scope. |
| **D2** | What-if inputs: only hypotheses the policy can use, or free text? | **Policy-bound hypotheses only.** Free text would bring the model into the simulator and break the prediction = reality gate. |
| **D3** | Add a second payer policy (Demo Payer B, 20 cases) in M3? | **Yes.** It is the cheapest proof that policies are configuration, and it surfaces engine gaps now rather than at pilot. |
| **D4** | Work-queue priority: the simple stated formula, or something learned? | **The stated formula**, shown in the UI. No data exists to learn from, and officers need to see why a case is first. |
| **D5** | Re-analyse automatically when an addendum is saved? | **Yes**, in the same transaction, so a case is never left with an answered query and a stale score. |

**Next step:** approve or amend D1–D5. On approval, work starts on `feat/m3-readiness` with M3-01.
