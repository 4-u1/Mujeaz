"""A2 Evidence Hunter — searches the whole patient record for each requirement.

Retrieval: BM25 over sentence chunks of every document (Arabic + English
normalisation and light stemming). Classification: deterministic over the
verified facts from A1, so a status is always backed by spans in the record.
"""

import math
from collections import Counter
from typing import Any

from app.agents.types import Document, EvidenceResult, Fact
from app.nlp.chunker import chunk
from app.nlp.text import tokens


def bm25_rank(documents: tuple[Document, ...], query: str, k: int = 5) -> list[tuple[str, int, int, float]]:
    chunks = [(d.doc_ref, c.start, c.end, tokens(c.text)) for d in documents for c in chunk(d.text)]
    if not chunks:
        return []
    q = set(tokens(query))
    n = len(chunks)
    avg = sum(len(t) for *_, t in chunks) / n or 1.0
    df = Counter(term for *_, t in chunks for term in set(t))
    scored = []
    for ref, s, e, toks in chunks:
        tf = Counter(toks)
        score = 0.0
        for term in q:
            if term not in tf:
                continue
            idf = math.log(1 + (n - df[term] + 0.5) / (df[term] + 0.5))
            f = tf[term]
            score += idf * f * 2.2 / (f + 1.2 * (0.25 + 0.75 * len(toks) / avg))
        scored.append((ref, s, e, round(score, 4)))
    scored.sort(key=lambda x: (-x[3], x[0], x[1]))
    return [x for x in scored[:k] if x[3] > 0]


def evaluate_requirement(req_id: str, spec: dict[str, Any], facts: list[Fact], documents: tuple[Document, ...]) -> EvidenceResult:
    retrieved = tuple(bm25_rank(documents, f"{spec['query']['en']} {spec['query']['ar']}"))
    contradiction = [f for f in facts if f.label in spec.get("contradicted_by", [])]
    candidates = [f for f in facts if f.label == spec["fact_label"]]
    min_weeks = float(spec["min_weeks"])
    supporting = tuple(f for f in facts if f.label in spec.get("supporting_labels", []))

    full = [f for f in candidates if f.value.get("weeks", 0) >= min_weeks]
    short = [f for f in candidates if f not in full]
    if full and not contradiction:
        best = max(full, key=lambda f: f.value.get("weeks", 0))
        return EvidenceResult(req_id, "FOUND",
                              f"{best.value.get('weeks'):g} weeks documented in {best.doc_ref}.",
                              f"موثق {best.value.get('weeks'):g} أسابيع في {best.doc_ref}.",
                              (best, *supporting), retrieved)
    if short and not contradiction:
        best = max(short, key=lambda f: f.value.get("weeks", 0))
        wk = best.value.get("weeks")
        reason = (f"Only {wk:g} weeks documented (minimum {min_weeks:g})." if wk is not None
                  else "Therapy documented without a duration.")
        reason_ar = (f"موثق {wk:g} أسابيع فقط (الحد الأدنى {min_weeks:g})." if wk is not None
                     else "العلاج موثق دون مدة.")
        q_en = spec["cdi"]["en"]
        q_ar = spec["cdi"]["ar"]
        return EvidenceResult(req_id, "PARTIAL", reason, reason_ar, (best, *supporting), retrieved, q_en, q_ar)
    if contradiction:
        reason = "Therapy is claimed but the record shows it was not attended."
        reason_ar = "العلاج مذكور لكن السجل يُظهر عدم الحضور."
        facts_used = tuple(contradiction) + tuple(f for f in facts if f.label == "claimed_therapy")
        return EvidenceResult(req_id, "MISSING", reason, reason_ar, facts_used, retrieved,
                              spec["cdi"]["en"], spec["cdi"]["ar"])
    negated = tuple(f for f in facts if f.label == "therapy_negated")
    reason = "The record states no prior conservative therapy." if negated else \
        "No documented conservative therapy found in the record."
    reason_ar = "السجل يذكر عدم وجود علاج تحفظي سابق." if negated else "لم يُعثر على علاج تحفظي موثق في السجل."
    return EvidenceResult(req_id, "MISSING", reason, reason_ar, negated, retrieved, spec["cdi"]["en"], spec["cdi"]["ar"])
