"""Structured physician answers: validation, rendering, and round trip through A1."""

from datetime import date

import pytest
from pydantic import TypeAdapter, ValidationError

from app.agents.a1_baseline import extract
from app.agents.types import Document
from app.cdi.addendum import Answer, RedFlagAnswer, TherapyAnswer, render, validate_against_request

ADAPTER: TypeAdapter[TherapyAnswer | RedFlagAnswer] = TypeAdapter(Answer)


def therapy(**kw: object) -> TherapyAnswer:
    base = {"start_date": date(2026, 7, 1), "end_date": date(2026, 8, 12), "sessions": 8, "provider": "Demo Physio"}
    return TherapyAnswer(**{**base, **kw})  # type: ignore[arg-type]


def test_weeks_round_down() -> None:
    assert therapy().weeks == 6.0  # 42 days
    assert therapy(end_date=date(2026, 8, 11)).weeks == 5.8  # 41 days never reads as 6


@pytest.mark.parametrize("kw", [{"end_date": date(2026, 7, 1)}, {"sessions": 0}, {"sessions": 61},
                                {"provider": "x"}, {"start_date": date(2025, 6, 1)}])
def test_invalid_answers(kw: dict) -> None:  # type: ignore[type-arg]
    with pytest.raises(ValidationError):
        therapy(**kw)


def test_request_rules() -> None:
    with pytest.raises(ValueError, match="future"):
        validate_against_request(therapy(end_date=date(2026, 12, 1)), date(2026, 12, 5), date(2026, 10, 30))
    with pytest.raises(ValueError, match="before the request"):
        validate_against_request(therapy(end_date=date(2026, 9, 2)), date(2026, 9, 1), date(2026, 10, 30))
    validate_against_request(therapy(), date(2026, 9, 1), date(2026, 10, 30))


def test_discriminated_union() -> None:
    a = ADAPTER.validate_python({"kind": "red_flag", "finding": "cauda_equina", "observed_on": "2026-09-01"})
    assert isinstance(a, RedFlagAnswer)
    with pytest.raises(ValidationError):
        ADAPTER.validate_python({"kind": "free_text", "text": "trust me"})


@pytest.mark.parametrize("lang", ["en", "ar"])
@pytest.mark.parametrize(("answer", "labels"), [
    (therapy(nsaid="naproxen"), {"conservative_therapy", "medication"}),
    (therapy(end_date=date(2026, 8, 11), sessions=5), {"conservative_therapy"}),
    (RedFlagAnswer(finding="progressive_deficit", observed_on=date(2026, 9, 1)), {"red_flag"}),
])
def test_rendered_addendum_round_trips_through_a1(lang: str, answer: TherapyAnswer | RedFlagAnswer,
                                                  labels: set[str]) -> None:
    text = render(answer, case_number="SYN-MRI-001", language=lang, author="Dr. Khalid")  # type: ignore[arg-type]
    assert "SYN-MRI-001" in text and "Dr. Khalid" in text
    facts = extract((Document("A", "addendum", lang, date(2026, 9, 2), text),))
    assert {f.label for f in facts} == labels
    if isinstance(answer, TherapyAnswer):
        f = next(f for f in facts if f.label == "conservative_therapy")
        assert f.value == {"weeks": answer.weeks, "sessions": answer.sessions}
