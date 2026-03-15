"""오디오 WebSocket 응답 스키마."""

from __future__ import annotations

from pydantic import BaseModel


class StreamUtteranceItemResponse(BaseModel):
    """실시간 발화 응답 항목."""

    id: str
    seq_num: int
    segment_id: str | None = None
    text: str
    confidence: float
    start_ms: int
    end_ms: int
    is_partial: bool = False
    kind: str = "final"
    revision: int | None = None
    input_source: str | None = None
    stability: str | None = None


class StreamEventItemResponse(BaseModel):
    """실시간 이벤트 응답 항목."""

    id: str
    type: str
    title: str
    evidence_text: str | None = None
    state: str
    source_utterance_id: str | None = None
    speaker_label: str | None = None


class StreamPayloadResponse(BaseModel):
    """오디오 WebSocket 정상/오류 공용 응답."""

    session_id: str
    input_source: str | None = None
    utterances: list[StreamUtteranceItemResponse]
    events: list[StreamEventItemResponse]
    error: str | None = None
