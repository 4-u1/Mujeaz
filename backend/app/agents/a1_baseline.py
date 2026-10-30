"""A1 Clinical Understanding — deterministic baseline.

Classifies each sentence of each document into at most one clinical fact label
using bilingual cue lists, extracts numeric values from the verified sentence,
and returns facts whose span is the sentence itself (so spans are exact by
construction). It is the CI baseline and the fallback when no model is available.
"""

import re

from app.agents.numbers import find_sessions, find_weeks
from app.agents.types import Document, Fact
from app.nlp.chunker import chunk
from app.nlp.text import normalize


def _any(text: str, cues: tuple[str, ...]) -> bool:
    return any(c in text for c in cues)


THERAPY = ("physio", "physical therap", "physiother", "علاج طبيعي", "علاج الطبيعي", "علاج فيزيائي",
           "علاج الفيزيائي", "العلاج الطبيعي")
NEGATION = ("no prior physio", "no physio", "no prior physical", "never had physio", "without any physio",
            "not received physio", "لم يتلق", "لم يتلقى", "لا يوجد علاج", "لم يخضع")
NOT_ATTENDED = ("did not attend", "no-show", "no show", "missed all", "لم يحضر", "تغيب عن", "تغيّب عن")
CLAIM = ("reports having", "states ", "reportedly", "claims", "يذكر", "يفيد", "حسب قول")
PERSIST = ("persist", "no improvement", "no meaningful improvement", "not improved", "مستمرة", "لا يوجد تحسن",
           "دون تحسن ملحوظ")
RED_FLAG = ("saddle", "cauda equina", "urinary retention", "bladder", "bowel incontinence", "perineal",
            "foot drop", "progressive weakness", "progressive neurolog", "خدر سرجي", "احتباس بولي", "المثانه",
            "العجان", "ذنب الفرس", "ضعف متزايد")
EXAM = ("straight leg raise", "slr", "رفع الساق المستقيمه", "لاسيغ", "لازيغ")
PAIN = ("pain", "sciatica", "الم", "عرق النسا")
MRI = ("mri", "magnetic resonance", "رنين مغناطيسي")
LUMBAR = ("lumbar", "قطني", "القطنيه", "القطني")
DRUGS = ("naproxen", "ibuprofen", "diclofenac", "celecoxib", "meloxicam", "etoricoxib", "nsaid trial",
         "نابروكسين", "ايبوبروفين", "ديكلوفيناك", "سيليكوكسيب", "ميلوكسيكام", "مضاد التهاب", "مضادات الالتهاب")


def classify(sentence: str) -> str | None:
    """Single most specific label for a sentence, or None."""
    t = normalize(sentence)
    therapy = _any(t, tuple(normalize(c) for c in THERAPY))
    if therapy and _any(t, tuple(normalize(c) for c in NEGATION)):
        return "therapy_negated"
    if _any(t, tuple(normalize(c) for c in NOT_ATTENDED)):
        return "therapy_not_attended"
    if _any(t, tuple(normalize(c) for c in RED_FLAG)):
        return "red_flag"
    if _any(t, tuple(normalize(c) for c in EXAM)):
        return "exam_slr"
    if _any(t, tuple(normalize(c) for c in MRI)) and _any(t, tuple(normalize(c) for c in LUMBAR)):
        return "requested_service"
    numbers = find_weeks(t) is not None or find_sessions(t) is not None
    if _any(t, tuple(normalize(c) for c in PERSIST)) and not numbers:
        return "persistent_symptoms"
    if therapy and _any(t, tuple(normalize(c) for c in CLAIM)) and not numbers:
        return "claimed_therapy"
    if therapy and numbers:
        return "conservative_therapy"
    if _any(t, tuple(normalize(c) for c in DRUGS)):
        return "medication"
    if _any(t, tuple(normalize(c) for c in PAIN)) and find_weeks(t) is not None:
        return "symptom_duration"
    return None


_TRAIL = re.compile(r"[\s.!?؟،,;:]+$")


def extract_document(doc: Document) -> list[Fact]:
    facts: list[Fact] = []
    for c in chunk(doc.text):
        label = classify(c.text)
        if label is None:
            continue
        trimmed = _TRAIL.sub("", c.text)
        end = c.start + len(trimmed)
        quote = doc.text[c.start:end]
        value: dict[str, float] = {}
        weeks, sessions = find_weeks(quote), find_sessions(quote)
        if weeks is not None and label in ("conservative_therapy", "symptom_duration"):
            value["weeks"] = weeks
        if sessions is not None and label == "conservative_therapy":
            value["sessions"] = sessions
        facts.append(Fact(label=label, doc_ref=doc.doc_ref, start=c.start, end=end, quote=quote, value=value,
                          fact_date=doc.authored_on, confidence=80, source="baseline"))
    return facts


def extract(documents: tuple[Document, ...]) -> list[Fact]:
    out: list[Fact] = []
    for d in documents:
        out.extend(extract_document(d))
    return out
