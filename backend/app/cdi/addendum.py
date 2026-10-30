"""Structured physician answers and the addendum text rendered from them.

The same renderer serves the what-if simulator and the real answer, so a simulation
and the re-analysis after the real addendum see identical text (M3 eval gate).
"""

import math
from datetime import date
from typing import Annotated, Literal

from pydantic import BaseModel, Field, model_validator

RED_FLAGS: dict[str, tuple[str, str]] = {
    "cauda_equina": ("cauda equina signs with saddle anaesthesia", "علامات متلازمة ذنب الفرس مع خدر سرجي"),
    "progressive_deficit": ("progressive weakness of the leg", "ضعف متزايد في الساق"),
    "urinary_retention": ("urinary retention", "احتباس بولي"),
}
NSAIDS: dict[str, tuple[str, str]] = {
    "naproxen": ("naproxen", "نابروكسين"), "ibuprofen": ("ibuprofen", "ايبوبروفين"),
    "diclofenac": ("diclofenac", "ديكلوفيناك"), "celecoxib": ("celecoxib", "سيليكوكسيب"),
}


class TherapyAnswer(BaseModel):
    """Conservative therapy that was delivered before the request."""

    kind: Literal["therapy"] = "therapy"
    start_date: date
    end_date: date
    sessions: int = Field(ge=1, le=60)
    provider: str = Field(min_length=2, max_length=120)
    nsaid: Literal["naproxen", "ibuprofen", "diclofenac", "celecoxib"] | None = None

    @model_validator(mode="after")
    def _dates(self) -> "TherapyAnswer":
        if self.end_date <= self.start_date:
            raise ValueError("end_date must be after start_date")
        if (self.end_date - self.start_date).days > 366:
            raise ValueError("therapy period longer than a year; split it or document it in the record")
        return self

    @property
    def weeks(self) -> float:
        """Whole tenths of a week, rounded down so 41 days never reads as 6 weeks."""
        return math.floor((self.end_date - self.start_date).days * 10 / 7) / 10


class RedFlagAnswer(BaseModel):
    kind: Literal["red_flag"] = "red_flag"
    finding: Literal["cauda_equina", "progressive_deficit", "urinary_retention"]
    observed_on: date


Answer = Annotated[TherapyAnswer | RedFlagAnswer, Field(discriminator="kind")]


def validate_against_request(answer: TherapyAnswer | RedFlagAnswer, requested_on: date, today: date) -> None:
    """Rules that need the case: no future dates, and therapy must precede the request (decision D1)."""
    last = answer.end_date if isinstance(answer, TherapyAnswer) else answer.observed_on
    if last > today:
        raise ValueError("dates cannot be in the future")
    if isinstance(answer, TherapyAnswer) and answer.end_date > requested_on:
        raise ValueError("therapy must have ended on or before the request date; a later course needs a new request")


def render(answer: TherapyAnswer | RedFlagAnswer, *, case_number: str, language: Literal["en", "ar"],
           author: str) -> str:
    if isinstance(answer, TherapyAnswer):
        w, n = f"{answer.weeks:g}", answer.sessions
        if language == "ar":
            lines = [f"ملحق الطبيب للطلب {case_number} (بعد تقديم الطلب).",
                     f"أكمل المريض العلاج الطبيعي: {n} جلسات خلال {w} أسابيع.",
                     f"الفترة من {answer.start_date.isoformat()} إلى {answer.end_date.isoformat()}، "
                     f"مقدم الخدمة: {answer.provider}."]
            if answer.nsaid:
                lines.append(f"وُصف {NSAIDS[answer.nsaid][1]} خلال الفترة نفسها.")
        else:
            lines = [f"Physician addendum to request {case_number} (written after the request).",
                     f"Completed physiotherapy: {n} sessions over {w} weeks.",
                     f"Period {answer.start_date.isoformat()} to {answer.end_date.isoformat()}, "
                     f"provider: {answer.provider}."]
            if answer.nsaid:
                lines.append(f"Prescribed {NSAIDS[answer.nsaid][0]} during the same period.")
    else:
        en, ar = RED_FLAGS[answer.finding]
        if language == "ar":
            lines = [f"ملحق الطبيب للطلب {case_number} (بعد تقديم الطلب).",
                     f"مؤشر خطير: {ar}، بتاريخ {answer.observed_on.isoformat()}."]
        else:
            lines = [f"Physician addendum to request {case_number} (written after the request).",
                     f"Red-flag finding: {en}, observed on {answer.observed_on.isoformat()}."]
    lines.append(f"— {author}" if language == "en" else f"— {author}")
    return "\n".join(lines)
