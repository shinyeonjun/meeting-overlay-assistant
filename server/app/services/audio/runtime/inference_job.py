"""실시간 추론 작업 모델."""

from __future__ import annotations

from dataclasses import dataclass, field
import time


@dataclass(slots=True)
class InferenceJob:
    """워커가 처리할 하나의 추론 작업."""

    context_id: str
    session_id: str
    input_source: str | None
    stream_kind: str
    kind: str
    priority: str
    chunk: bytes
    created_at_monotonic: float = field(default_factory=time.monotonic)
