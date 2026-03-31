"""발화 엔티티."""

from __future__ import annotations

from dataclasses import dataclass
from uuid import uuid4


@dataclass(frozen=True)
class Utterance:
    """발화 텍스트 엔티티."""

    id: str
    session_id: str
    seq_num: int
    start_ms: int
    end_ms: int
    text: str
    confidence: float
    input_source: str | None = None
    stt_backend: str | None = None
    latency_ms: int | None = None

    @classmethod
    def create(
        cls,
        session_id: str,
        seq_num: int,
        start_ms: int,
        end_ms: int,
        text: str,
        confidence: float,
        input_source: str | None = None,
        stt_backend: str | None = None,
        latency_ms: int | None = None,
    ) -> "Utterance":
        """새 발화를 생성한다."""
        return cls(
            id=f"utt-{uuid4().hex}",
            session_id=session_id,
            seq_num=seq_num,
            start_ms=start_ms,
            end_ms=end_ms,
            text=text,
            confidence=confidence,
            input_source=input_source,
            stt_backend=stt_backend,
            latency_ms=latency_ms,
        )
