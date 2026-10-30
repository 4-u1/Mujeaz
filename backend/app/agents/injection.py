"""Prompt-injection detector. Flags text that tries to instruct the system.

Detection is recorded for reviewers; it never changes outcomes, which are decided
by the verifier and the rules engine, not by instructions inside clinical text.
"""

import re

from app.agents.types import Document, InjectionFlag
from app.nlp.chunker import chunk
from app.nlp.text import normalize

_PATTERNS = [re.compile(p) for p in (
    # English: overriding instructions, addressing the model, dictating outcomes
    r"\b(ignore|disregard|forget|override|bypass)\b.{0,30}\b(instructions?|polic(y|ies)|rules?|guidelines?|prompt)\b",
    r"\b(system|admin|developer)\s*(note|override|prompt|message|mode)\b",
    r"\b(note|message|instructions?)\s+(to|for)\s+(the\s+)?(ai|assistant|model|reviewer|system)\b",
    r"\b(you|assistant|ai|model)\b.{0,20}\b(must|should|shall)\s+(approve|accept|pass|mark)\b",
    r"\b(set|change|make)\b.{0,20}\b(readiness|risk)?\s*score\b.{0,10}\b(to|=)\s*\d+",
    r"\b(mark|treat|consider)\b.{0,30}\b(as\s+)?(passed|approved|satisfied|met)\b",
    r"\b(respond|reply|answer|output)\s+(only\s+)?(with|:)|\boutput\s+decision_ready\b",
    # Arabic (normalised: alef/ta-marbuta/ya folded)
    r"(تجاهل|تجاهلي|اهمل|تخط|انس)\s+.{0,20}(التعليمات|تعليمات|السياسه|القواعد|الشروط)",
    r"(تعليمات|ملاحظه|رساله)\s+(لل|الي\s+ال)(نظام|مساعد|ذكاء|نموذج|مراجع)",
    r"(لا|عدم)\s+(تطبق|تطبيق)\s+(السياسه|القواعد|الشروط)",
    r"(اعتبر|اعتبري|سجل)\s+.{0,25}(مستوفا|مستوفي|مقبول|جاهز|ناجح)",
    r"(وافق|اقبل|اعتمد)\s+(علي\s+)?(الطلب|هذا\s+الطلب)",
)]


def detect(documents: tuple[Document, ...]) -> list[InjectionFlag]:
    flags: list[InjectionFlag] = []
    for d in documents:
        for c in chunk(d.text):
            t = normalize(c.text)
            if any(p.search(t) for p in _PATTERNS):
                flags.append(InjectionFlag(d.doc_ref, c.start, c.end, c.text))
    return flags
