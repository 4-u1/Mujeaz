"""Number parsing for clinical text: digits, Arabic-Indic digits and number words (en/ar)."""

import re

_EN = {"one": 1, "two": 2, "three": 3, "four": 4, "five": 5, "six": 6, "seven": 7, "eight": 8, "nine": 9,
       "ten": 10, "eleven": 11, "twelve": 12, "thirteen": 13, "fourteen": 14, "fifteen": 15, "sixteen": 16,
       "seventeen": 17, "eighteen": 18, "nineteen": 19, "twenty": 20}
_AR = [("ثلاث", 3), ("اربع", 4), ("أربع", 4), ("خمس", 5), ("ست", 6), ("سبع", 7), ("ثمان", 8), ("تسع", 9),
       ("عشر", 10), ("اثن", 2), ("واحد", 1)]
_INDIC = str.maketrans("٠١٢٣٤٥٦٧٨٩۰۱۲۳۴۵۶۷۸۹", "01234567890123456789")

NUM = r"(?:[0-9٠-٩۰-۹]+(?:\.[0-9]+)?|" + "|".join(sorted(_EN, key=len, reverse=True)) + r"|(?:ثلاث|[اأ]ربع|خمس|ست|سبع|ثمان|تسع|عشر|اثن)\w*)"
_NUM_RE = re.compile(NUM, re.IGNORECASE)


def parse_number(token: str) -> float | None:
    t = token.strip().lower().translate(_INDIC)
    if re.fullmatch(r"[0-9]+(?:\.[0-9]+)?", t):
        return float(t)
    if t in _EN:
        return float(_EN[t])
    for stem, v in _AR:
        if t.startswith(stem):
            return float(v)
    return None


WEEK_WORDS = r"(?:weeks?|wks?|أسابيع|اسابيع|أسبوع|اسبوع|أسبوعا|اسبوعا)"
SESSION_WORDS = r"(?:sessions?|visits?|appointments?|جلسات|جلسة)"
_WEEKS = re.compile(rf"({NUM})\s*[- ]?\s*{WEEK_WORDS}", re.IGNORECASE)
_SESSIONS = re.compile(rf"({NUM})\s+(?:\w+\s+){{0,2}}?{SESSION_WORDS}", re.IGNORECASE)


def find_weeks(text: str) -> float | None:
    m = _WEEKS.search(text)
    return parse_number(m.group(1)) if m else None


def find_sessions(text: str) -> float | None:
    m = _SESSIONS.search(text)
    return parse_number(m.group(1)) if m else None


def has_number(text: str) -> bool:
    return bool(_NUM_RE.search(text))
