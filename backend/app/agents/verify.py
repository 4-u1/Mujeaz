"""Span verifier (non-negotiable rule 1: No Evidence, No Claim).

Agents return quotes, never offsets. The verifier finds the quote in the source
document and computes the offsets itself. A quote that is not in the document
is rejected.
"""

from dataclasses import dataclass

from app.nlp.text import normalize_with_map


@dataclass(frozen=True)
class Located:
    start: int
    end: int
    exact: bool


def locate(quote: str, document: str, hint_start: int = 0) -> Located | None:
    q = quote.strip()
    if len(q) < 3:
        return None
    pos = document.find(q, hint_start)
    if pos < 0:
        pos = document.find(q)
    if pos >= 0:
        return Located(pos, pos + len(q), True)
    nq, _ = normalize_with_map(q)
    nd, mapping = normalize_with_map(document)
    npos = nd.find(nq.strip())
    if npos < 0 or not nq.strip():
        return None
    start = mapping[npos]
    end = mapping[npos + len(nq.strip()) - 1] + 1
    return Located(start, end, False)


def verified_quote(document: str, located: Located) -> str:
    return document[located.start:located.end]
