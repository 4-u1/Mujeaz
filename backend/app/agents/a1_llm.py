"""A1 Clinical Understanding — LLM mode. Same output as the baseline, verified the same way.

The model returns labels and quotes only. Offsets are computed by the verifier and
numbers are parsed from the verified text, never taken from the model.
"""

from dataclasses import dataclass
from typing import Literal

from pydantic import BaseModel, Field

from app.agents.numbers import find_sessions, find_weeks
from app.agents.types import FACT_LABELS, Document, Fact
from app.agents.verify import locate
from app.llm.provider import Provider, Usage, load_prompt

Label = Literal[
    "symptom_duration", "exam_slr", "conservative_therapy", "medication", "persistent_symptoms", "red_flag",
    "claimed_therapy", "therapy_not_attended", "therapy_negated", "requested_service",
]


class LlmFact(BaseModel):
    label: Label
    quote: str = Field(min_length=3, max_length=600)


class LlmFacts(BaseModel):
    facts: list[LlmFact]


@dataclass(frozen=True)
class LlmRun:
    facts: list[Fact]
    rejected: list[str]  # quotes that were not found in the document (hallucinations)
    usage: list[Usage]
    prompt_version: str


def extract(documents: tuple[Document, ...], provider: Provider) -> LlmRun:
    prompt = load_prompt("a1_extract")
    facts: list[Fact] = []
    rejected: list[str] = []
    usage: list[Usage] = []
    for d in documents:
        out, u = provider.generate(prompt, {"doc_ref": d.doc_ref, "doc_type": d.doc_type, "text": d.text}, LlmFacts)
        usage.append(u)
        for f in out.facts:
            if f.label not in FACT_LABELS:
                continue
            loc = locate(f.quote, d.text)
            if loc is None:
                rejected.append(f.quote)
                continue
            quote = d.text[loc.start:loc.end]
            value: dict[str, float] = {}
            weeks, sessions = find_weeks(quote), find_sessions(quote)
            if weeks is not None and f.label in ("conservative_therapy", "symptom_duration"):
                value["weeks"] = weeks
            if sessions is not None and f.label == "conservative_therapy":
                value["sessions"] = sessions
            facts.append(Fact(f.label, d.doc_ref, loc.start, loc.end, quote, value, d.authored_on, 85, "llm"))
    return LlmRun(facts, rejected, usage, f"a1_extract@{prompt.version}")
