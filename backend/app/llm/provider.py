"""LLM provider interface, prompt registry and the Gemini / Replay implementations."""

import hashlib
import json
import time
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any, Protocol, TypeVar

from pydantic import BaseModel

PROMPT_DIR = Path(__file__).resolve().parents[1] / "prompts"
T = TypeVar("T", bound=BaseModel)


@dataclass(frozen=True)
class Prompt:
    name: str
    version: str
    system: str
    template: str

    @property
    def sha256(self) -> str:
        return hashlib.sha256(f"{self.system}\n---\n{self.template}".encode()).hexdigest()


@lru_cache
def load_prompt(name: str) -> Prompt:
    """Prompt files: `<name>.md` with a `version:` first line, then `## system` and `## user` sections."""
    raw = (PROMPT_DIR / f"{name}.md").read_text(encoding="utf-8")
    header, _, rest = raw.partition("\n")
    version = header.split(":", 1)[1].strip()
    system = rest.split("## system", 1)[1].split("## user", 1)[0].strip()
    template = rest.split("## user", 1)[1].strip()
    return Prompt(name, version, system, template)


@dataclass(frozen=True)
class Usage:
    model: str
    latency_ms: int
    tokens_in: int | None = None
    tokens_out: int | None = None


class Provider(Protocol):
    name: str

    def generate(self, prompt: Prompt, inputs: dict[str, str], schema: type[T]) -> tuple[T, Usage]: ...


def inputs_hash(prompt: Prompt, inputs: dict[str, str]) -> str:
    return hashlib.sha256(json.dumps({"p": prompt.sha256, "i": inputs}, sort_keys=True,
                                     ensure_ascii=False).encode()).hexdigest()


class GeminiProvider:
    name = "gemini"

    def __init__(self, api_key: str, model: str) -> None:
        from google import genai

        self._client = genai.Client(api_key=api_key)
        self.model = model

    def generate(self, prompt: Prompt, inputs: dict[str, str], schema: type[T]) -> tuple[T, Usage]:
        from google.genai import types

        t0 = time.perf_counter()
        resp = self._client.models.generate_content(
            model=self.model, contents=prompt.template.format(**inputs),
            config=types.GenerateContentConfig(system_instruction=prompt.system, temperature=0,
                                               response_mime_type="application/json", response_schema=schema))
        meta: Any = getattr(resp, "usage_metadata", None)
        usage = Usage(self.model, int((time.perf_counter() - t0) * 1000),
                      getattr(meta, "prompt_token_count", None), getattr(meta, "candidates_token_count", None))
        return schema.model_validate_json(resp.text or "{}"), usage


class ReplayProvider:
    """Replays recorded responses (fixtures) keyed by prompt + inputs hash; records when wrapping a live provider."""

    name = "replay"

    def __init__(self, fixture_dir: Path, live: Provider | None = None) -> None:
        self.dir = fixture_dir
        self.live = live

    def generate(self, prompt: Prompt, inputs: dict[str, str], schema: type[T]) -> tuple[T, Usage]:
        key = inputs_hash(prompt, inputs)
        path = self.dir / f"{prompt.name}-{prompt.version}-{key[:24]}.json"
        if path.exists():
            data = json.loads(path.read_text(encoding="utf-8"))
            return schema.model_validate(data["output"]), Usage(data["model"], 0)
        if self.live is None:
            raise LookupError(f"no recorded response for {prompt.name} {key[:12]}")
        out, usage = self.live.generate(prompt, inputs, schema)
        self.dir.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps({"model": usage.model, "output": out.model_dump()}, ensure_ascii=False, indent=1),
                        encoding="utf-8")
        return out, usage
