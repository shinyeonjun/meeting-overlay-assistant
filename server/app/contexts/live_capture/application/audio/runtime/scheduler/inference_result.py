"""실시간 추론 결과 모델."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(slots=True)
class InferenceResult:
    """워커 처리 결과를 sender 루프로 전달하는 모델."""

    utterances: list[object] = field(default_factory=list)
    events: list[object] = field(default_factory=list)
    error_message: str | None = None
    terminal: bool = False

    @classmethod
    def payload(cls, *, utterances: list[object], events: list[object]) -> "InferenceResult":
        return cls(utterances=utterances, events=events)

    @classmethod
    def error(cls, message: str) -> "InferenceResult":
        return cls(error_message=message)

    @classmethod
    def terminal_result(cls) -> "InferenceResult":
        return cls(terminal=True)

