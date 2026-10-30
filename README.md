<div align="center">

# مُجاز · Mujeaz

### AI Revenue Assurance & Prior-Authorization Command Center for Saudi Healthcare

**نمنع الرفض. نحمي الإيراد. نستعيد المفقود.**
*Prevent the denial. Protect the revenue. Recover the lost.*

![Status](https://img.shields.io/badge/status-prototype-orange)
![Stack](https://img.shields.io/badge/stack-React%2019%20·%20Express%20·%20Gemini-blue)
![Standards](https://img.shields.io/badge/target-HL7%20FHIR%20R4%20·%20NPHIES-teal)
![UI](https://img.shields.io/badge/UI-Arabic%20RTL--first-green)

Designed & built by **Yazeed Hamad Alharthi · يزيد حمد الحارثي**

</div>

---

## نبذة | Overview

**مُجاز** طبقة ذكاء تشغيلية تعمل بين الأنظمة السريرية (HIS/EMR) والمسار التأميني (NPHIES). تقرأ الطلب السريري، تبحث عن الأدلة الداعمة داخل السجل الطبي، تطابقها مع سياسة شركة التأمين، وتحسب جاهزية الطلب قبل إرساله. وإذا رُفض الطلب، تبني حزمة استئناف موثقة بالمصادر وجاهزة للمراجعة البشرية.

**Mujeaz** is an intelligence layer that sits between clinical systems and the payer channel. It works **before, during and after** a denial:

```
Prevent → Approve → Monitor → Recover → Learn
```

| Without Mujeaz | Appeal-only tools | Mujeaz |
|---|---|---|
| Submit → Wait → Denied → Manual work | Denied → Appeal | Understand → Validate → Predict → Complete → Submit → Monitor → Recover → Learn |

---

## ⚠️ Project status — read first

This repository is a **functional prototype / demo**, not a production system.

| Area | Current state |
|---|---|
| Clinical data | Synthetic mock cases (`src/data/mockCases.ts`). No real patient data. |
| Payers & policies | Payer names are used for illustration only. Policy codes and rules are **fictional** and do not represent any insurer's actual coverage terms. |
| NPHIES | **Not connected.** All submissions and payer responses are simulated. |
| AI analysis | Live via Google Gemini when `GEMINI_API_KEY` is set; otherwise a static fallback is returned. |
| Persistence | In-memory React state only. Refreshing the page resets everything. |
| Auth / RBAC | Not implemented. |

See [`docs/PRD.md`](docs/PRD.md) for the full product requirements, the gap analysis against this codebase, and the roadmap to a production-grade system.

---

## Core concepts

### Multi-agent pipeline

| ID | Agent | Responsibility | Prototype status |
|---|---|---|---|
| A1 | Clinical Understanding | Turn free-text notes into structured, source-linked clinical facts | LLM (Gemini) in Sandbox; mocked elsewhere |
| A2 | Evidence Hunter | Search the patient record for proof that each policy requirement is met | Mocked (state transition) |
| A3 | Policy Reasoning | Match the request against payer coverage rules (RAG + deterministic rules) | LLM-generated; no rules engine yet |
| A4 | NPHIES / FHIR Conformance | Build and validate the FHIR bundle before submission | Static JSON sample; no validation |
| A5 | Revenue Risk | Revenue at risk, denial risk, recoverable value, priority | LLM-generated / mocked |
| A6 | Recovery | Root-cause the denial and build an Appeal Evidence Map + letters | LLM (Gemini) via `/api/ai/generate-appeal` |

### Mujeaz Readiness Score

A 0–100 score of how ready a request is to submit — **not** a prediction that the payer will approve. Six components:

`Clinical Evidence · Policy Match · Documentation · Coding Integrity · Required Attachments · Administrative Completeness`

The system must always explain what is keeping a request below 100.

### "No Evidence, No Claim"

Every clinical fact the system relies on must carry **Fact + Source + Date + Confidence**. If no evidence is found, the system reports it as missing — it never invents it.

---

## Features in the app

| Tab | What it shows |
|---|---|
| **Command Center** | Revenue protected / at risk / recovered, prevented denials, active authorizations, recovery queue |
| **Live Walkthrough** | Guided 7-stage demo: MRI Lumbar Spine request → risk detected → evidence found → policy satisfied → readiness 98/100 → FHIR → approval; plus a denial → recovery scenario |
| **Digital Twin Inspector** | Per-case view: clinical facts, policy rules, evidence, agent runs, FHIR payload, audit trail |
| **AI Sandbox** | Paste any clinical note (Arabic or English) and run live analysis through Gemini |
| **Recovery Queue** | Denied cases and AI-generated appeal packages (Arabic + English letters) |
| **Policy RAG** | Browsable sample payer policy knowledge base |

All screens are bilingual with Arabic RTL as the default.

---

## Architecture (prototype)

```
┌──────────────────────────── Browser ─────────────────────────────┐
│ React 19 + Vite + Tailwind v4 + motion + lucide-react            │
│ Command Center · Walkthrough · Digital Twin · Sandbox · Recovery │
└───────────────────────────────┬──────────────────────────────────┘
                                │ fetch /api/*
┌───────────────────────────────▼──────────────────────────────────┐
│ Express server (server.ts)                                       │
│  GET  /api/health                                                │
│  POST /api/ai/analyze-order   → A1/A3/A5 analysis (Gemini)        │
│  POST /api/ai/generate-appeal → A6 appeal package (Gemini)        │
│  Vite middleware in dev · static dist/ in prod                   │
└───────────────────────────────┬──────────────────────────────────┘
                                │ structured JSON output (responseSchema)
                       ┌────────▼────────┐
                       │  Google Gemini  │
                       └─────────────────┘
```

Target production architecture (FastAPI services, PostgreSQL + pgvector, rules engine, evidence graph, NPHIES gateway) is specified in [`docs/PRD.md`](docs/PRD.md#9-target-architecture).

---

## Getting started

**Requirements:** Node.js 20+ and a Gemini API key (optional — the app runs without it using fallback data).

```bash
git clone https://github.com/4-u1/Mujeaz.git
cd Mujeaz
npm install
cp .env.example .env.local     # then set GEMINI_API_KEY
npm run dev                    # http://localhost:3000
```

| Script | Purpose |
|---|---|
| `npm run dev` | Start Express + Vite dev server on port 3000 |
| `npm run build` | Build the client to `dist/` and bundle the server to `dist/server.cjs` |
| `npm start` | Run the production build |
| `npm run lint` | Type-check with `tsc --noEmit` |

### Environment variables

| Name | Required | Description |
|---|---|---|
| `GEMINI_API_KEY` | No | Enables live AI analysis. Server-side only; never exposed to the browser. |
| `APP_URL` | No | Public URL of the deployment. |

---

## API

### `POST /api/ai/analyze-order`

```json
{
  "clinicalNoteText": "45M, low back pain radiating to left leg for 8 weeks ... requesting MRI lumbar spine.",
  "payerName": "Sample Payer",
  "requestedService": "MRI Lumbar Spine"
}
```

Returns diagnosis and procedure codes, clinical facts with sources and confidence, policy rule results, the readiness breakdown, revenue risk, and evidence-hunter findings. Schema: `AnalyzeOrderResult` in [`server/geminiService.ts`](server/geminiService.ts).

### `POST /api/ai/generate-appeal`

Body: a `ClaimDigitalTwin` (see [`src/types.ts`](src/types.ts)). Returns `formalLetterEn`, `formalLetterAr`, `appealStrategy`, `appealStrategyAr`, `appealStrength`.

### `GET /api/health`

Liveness check.

---

## Project structure

```
.
├── server.ts                    # Express server + API routes
├── server/
│   └── geminiService.ts         # Gemini calls, JSON schemas, fallback analysis
├── src/
│   ├── App.tsx                  # App shell, tab routing, state
│   ├── types.ts                 # Domain model (ClaimDigitalTwin, ReadinessBreakdown, …)
│   ├── data/mockCases.ts        # Synthetic cases + initial dashboard metrics
│   └── components/
│       ├── ExecutiveDashboard.tsx
│       ├── LiveWalkthrough.tsx
│       ├── DigitalTwinInspector.tsx
│       ├── AISandbox.tsx
│       ├── RecoveryQueue.tsx
│       ├── PolicyKnowledgeBase.tsx
│       ├── Navbar.tsx
│       └── Footer.tsx
├── docs/
│   └── PRD.md                   # Product Requirements Document
└── public/                      # Logos
```

---

## Roadmap

| Phase | Focus |
|---|---|
| 1 — Intelligence | Clinical extraction, evidence retrieval, policy matching |
| 2 — Decision Readiness | Readiness Score, coding validation, document completeness |
| 3 — Interoperability | FHIR R4 profiles, NPHIES sandbox integration, payer responses |
| 4 — Revenue Recovery | Denial intelligence, appeal generation, evidence packages |
| 5 — Predictive Revenue | Denial prediction, revenue-at-risk forecasting, recovery prioritization |
| 6 — Learning Network | Governed learning from denial and recovery outcomes |

The MVP covers **one end-to-end scenario: MRI Lumbar Spine**, then expands to CT, endoscopy and specialty drugs.

---

## Responsible AI & compliance

- Mujeaz is **decision support**. Every submission and appeal requires human review.
- It is not an insurer, a claims adjudicator, or an accredited NPHIES body.
- Production use requires compliance with the Saudi **Personal Data Protection Law (PDPL)**, **CHI** requirements for NPHIES integration, **NCA** cybersecurity controls, and the hosting facility's own policies.
- Patient data must not be used to train models without an appropriate legal and contractual basis.

---

## Author

**Yazeed Hamad Alharthi · يزيد حمد الحارثي**
Developer · AI Engineering — Saudi Arabia
GitHub: [@4-u1](https://github.com/4-u1)

---

## License

The source files carry the `Apache-2.0` SPDX header. Add a root `LICENSE` file to make the license explicit.
