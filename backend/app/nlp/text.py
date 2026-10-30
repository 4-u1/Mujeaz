"""Arabic/English text normalisation that keeps a map back to the original offsets.

Used by the span verifier and retrieval. Normalisation never changes the stored
text; it only helps locate a quote, after which offsets refer to the original.
"""

import re
import unicodedata

_AR_DIACRITICS = set(chr(c) for c in range(0x064B, 0x0653)) | {"ٰ", "ـ"}  # harakat, dagger alif, tatweel
_FOLD = {
    "أ": "ا", "إ": "ا", "آ": "ا", "ٱ": "ا",
    "ى": "ي", "ئ": "ي", "ؤ": "و", "ة": "ه",
    "“": '"', "”": '"', "’": "'", "‘": "'", "–": "-", "—": "-", " ": " ",
}
_AR_INDIC = {chr(0x0660 + i): str(i) for i in range(10)} | {chr(0x06F0 + i): str(i) for i in range(10)}


def normalize_with_map(s: str) -> tuple[str, list[int]]:
    """Returns (normalised text, index map) where map[i] is the original index of normalised char i.

    Steps: NFKC per char, lower-case, drop Arabic diacritics/tatweel, fold letter variants,
    Arabic-Indic digits → ASCII, collapse whitespace runs to a single space.
    """
    out: list[str] = []
    idx: list[int] = []
    prev_space = False
    for i, ch in enumerate(s):
        if ch in _AR_DIACRITICS:
            continue
        ch = _AR_INDIC.get(ch, ch)
        ch = _FOLD.get(ch, ch)
        for c in unicodedata.normalize("NFKC", ch).lower():
            if c.isspace():
                if prev_space:
                    continue
                c, prev_space = " ", True
            else:
                prev_space = False
            out.append(c)
            idx.append(i)
    return "".join(out), idx


def normalize(s: str) -> str:
    return normalize_with_map(s)[0]


_WORD = re.compile(r"[0-9a-zء-ي]+")
_AR_PREFIXES = ("وال", "بال", "كال", "فال", "لل", "ال", "و", "ب", "ل", "ف")
_AR_SUFFIXES = ("ات", "ون", "ين", "ها", "ه", "ي")
_EN_SUFFIXES = ("ing", "ies", "es", "ed", "s")


def _stem(tok: str) -> str:
    if tok and "ء" <= tok[0] <= "ي":
        for p in _AR_PREFIXES:
            if tok.startswith(p) and len(tok) - len(p) >= 3:
                tok = tok[len(p):]
                break
        for sfx in _AR_SUFFIXES:
            if tok.endswith(sfx) and len(tok) - len(sfx) >= 3:
                tok = tok[: -len(sfx)]
                break
        return tok
    for sfx in _EN_SUFFIXES:
        if tok.endswith(sfx) and len(tok) - len(sfx) >= 3:
            return tok[: -len(sfx)]
    return tok


def tokens(s: str) -> list[str]:
    """Normalised, lightly stemmed word tokens (Arabic and English)."""
    return [_stem(t) for t in _WORD.findall(normalize(s))]
