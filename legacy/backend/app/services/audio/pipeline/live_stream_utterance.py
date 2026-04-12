"""실시간 partial/final payload용 발화 모델."""

from __future__ import annotations

from dataclasses import dataclass
from uuid import uuid4

from backend.app.domain.models.utterance import Utterance


@dataclass(frozen=True)
class LiveStreamUtterance:
    """DB 저장 여부와 무관하게 WebSocket payload에 실어 보내는 발화 모델."""

    id: str
    seq_num: int
    segment_id: str
    start_ms: int
    end_ms: int
    text: str
    confidence: float
    kind: str = "final"
    revision: int | None = None
    input_source: str | None = None
    stability: str | None = None

    @classmethod
    def create(
        cls,
        *,
        seq_num: int,
        segment_id: str,
        start_ms: int,
        end_ms: int,
        text: str,
        confidence: float,
        kind: str,
        revision: int | None = None,
        input_source: str | None = None,
        stability: str | None = None,
    ) -> "LiveStreamUtterance":
        """실시간 전송용 발화를 생성한다."""

        return cls(
            id=f"live-{uuid4().hex}",
            seq_num=seq_num,
            segment_id=segment_id,
            start_ms=start_ms,
            end_ms=end_ms,
            text=text,
            confidence=confidence,
            kind=kind,
            revision=revision,
            input_source=input_source,
            stability=stability,
        )

    @classmethod
    def from_utterance(
        cls,
        utterance: Utterance,
        *,
        segment_id: str,
        seq_num: int | None = None,
        input_source: str | None = None,
    ) -> "LiveStreamUtterance":
        """저장된 발화를 WebSocket 전송용 모델로 감싼다."""

        return cls(
            id=utterance.id,
            seq_num=seq_num if seq_num is not None else utterance.seq_num,
            segment_id=segment_id,
            start_ms=utterance.start_ms,
            end_ms=utterance.end_ms,
            text=utterance.text,
            confidence=utterance.confidence,
            kind="final",
            revision=None,
            input_source=input_source,
            stability="final",
        )
