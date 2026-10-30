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


def _documented(f: Fact, ar: bool = False) -> str:
    parts = []
    if f.value.get("weeks") is not None:
        w = f"{float(f.value['weeks']):g}"
        parts.append(f"{w} أسابيع" if ar else f"{w} weeks")
    if f.value.get("sessions") is not None:
        n = f"{float(f.value['sessions']):g}"
        parts.append(f"{n} جلسات" if ar else f"{n} sessions")
    return (" و" if ar else ", ").join(parts) or ("دون مدة أو عدد جلسات" if ar else "no duration or session count")


def _strength(f: Fact) -> tuple[float, float]:
    return float(f.value.get("weeks") or 0), float(f.value.get("sessions") or 0)


def evaluate_requirement(req_id: str, spec: dict[str, Any], facts: list[Fact], documents: tuple[Document, ...],
                         excluded_refs: frozenset[str] = frozenset()) -> EvidenceResult:
    """Classifies one requirement from verified facts.

    `excluded_refs` are documents the payer does not accept as evidence (post-request addenda when the
    policy says so). Their facts are still shown to reviewers, but cannot satisfy the requirement.
    """
    from app.rules.engine import describe, satisfies  # local import: engine imports agent types

    criteria = spec["satisfied_if"]
    need_en, need_ar = describe(criteria), describe(criteria, ar=True)
    retrieved = tuple(bm25_rank(documents, f"{spec['query']['en']} {spec['query']['ar']}"))
    usable = [f for f in facts if f.doc_ref not in excluded_refs]
    ignored = [f for f in facts if f.doc_ref in excluded_refs and f.label == spec["fact_label"]]
    contradiction = [f for f in usable if f.label in spec.get("contradicted_by", [])]
    candidates = [f for f in usable if f.label == spec["fact_label"]]
    supporting = tuple(f for f in usable if f.label in spec.get("supporting_labels", []))
    note_en = note_ar = ""
    if ignored and any(satisfies(criteria, f.value) for f in ignored):
        note_en = " A post-request addendum documents it, but this payer does not accept addenda."
        note_ar = " يوجد ملحق بعد الطلب يوثّقه، لكن هذه الجهة لا تقبل الملاحق."

    full = [f for f in candidates if satisfies(criteria, f.value)]
    short = [f for f in candidates if f not in full]
    if full and not contradiction:
        best = max(full, key=_strength)
        return EvidenceResult(req_id, "FOUND", f"Documented {_documented(best)} in {best.doc_ref} (requires {need_en}).",
                              f"موثق {_documented(best, True)} في {best.doc_ref} (المطلوب {need_ar}).",
                              (best, *supporting), retrieved)
    q_en, q_ar = spec["cdi"]["en"], spec["cdi"]["ar"]
    if short and not contradiction:
        best = max(short, key=_strength)
        return EvidenceResult(req_id, "PARTIAL",
                              f"Only {_documented(best)} documented (requires {need_en})." + note_en,
                              f"موثق {_documented(best, True)} فقط (المطلوب {need_ar})." + note_ar,
                              (best, *supporting), retrieved, q_en, q_ar)
    if contradiction:
        facts_used = tuple(contradiction) + tuple(f for f in usable if f.label == "claimed_therapy")
        return EvidenceResult(req_id, "MISSING", "Therapy is claimed but the record shows it was not attended." + note_en,
                              "العلاج مذكور لكن السجل يُظهر عدم الحضور." + note_ar, facts_used, retrieved, q_en, q_ar)
    negated = tuple(f for f in usable if f.label == "therapy_negated")
    reason = ("The record states no prior conservative therapy." if negated
              else "No documented conservative therapy found in the record.") + note_en
    reason_ar = ("السجل يذكر عدم وجود علاج تحفظي سابق." if negated
                 else "لم يُعثر على علاج تحفظي موثق في السجل.") + note_ar
    return EvidenceResult(req_id, "MISSING", reason, reason_ar, negated, retrieved, q_en, q_ar)
