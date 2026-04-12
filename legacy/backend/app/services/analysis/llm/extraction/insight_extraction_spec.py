"""인사이트 추출 LLM 스펙 로더."""

from __future__ import annotations

import json
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any

from backend.app.services.analysis.event_type_policy import (
    filter_insight_event_type_values,
)


DEFAULT_INSIGHT_EXTRACTION_SPEC_PATH = (
    Path(__file__).resolve().parents[5] / "config" / "insight_extraction.json"
)


@dataclass(frozen=True)
class InsightExtractionSpec:
    """인사이트 추출 프롬프트/스키마 스펙."""

    instruction: str
    max_candidates: int
    event_types: tuple[str, ...]
    states: tuple[str, ...]
    default_state_by_event_type: dict[str, str]
    default_priority_by_event_type: dict[str, int]
    few_shot_examples: tuple[dict[str, Any], ...]

    @classmethod
    def from_path(cls, path: str | Path) -> "InsightExtractionSpec":
        payload = json.loads(Path(path).read_text(encoding="utf-8"))
        event_types = filter_insight_event_type_values(payload.get("event_types", []))
        return cls(
            instruction=str(payload["instruction"]),
            max_candidates=int(payload.get("max_candidates", 3)),
            event_types=event_types,
            states=tuple(str(item) for item in payload.get("states", [])),
            default_state_by_event_type={
                str(key): str(value)
                for key, value in payload.get("default_state_by_event_type", {}).items()
                if str(key) in event_types
            },
            default_priority_by_event_type={
                str(key): int(value)
                for key, value in payload.get("default_priority_by_event_type", {}).items()
                if str(key) in event_types
            },
            few_shot_examples=tuple(payload.get("few_shot_examples", [])),
        )


@lru_cache(maxsize=4)
def load_insight_extraction_spec(path: str | Path | None = None) -> InsightExtractionSpec:
    """인사이트 추출 스펙을 캐시하여 로드한다."""
    target_path = Path(path) if path else DEFAULT_INSIGHT_EXTRACTION_SPEC_PATH
    return InsightExtractionSpec.from_path(target_path)
