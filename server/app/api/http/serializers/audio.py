"""오디오 WebSocket 직렬화 유틸."""

from __future__ import annotations

from server.app.api.http.schemas.audio import (
    StreamEventItemResponse,
    StreamPayloadResponse,
    StreamUtteranceItemResponse,
)


def build_stream_payload(
    session_id: str,
    utterances,
    events,
    *,
    input_source: str | None = None,
) -> dict:
    """실시간 발화/이벤트 결과를 공용 스키마로 직렬화한다."""

    def resolve_stability(utterance) -> str:
        stability = getattr(utterance, "stability", None)
        if isinstance(stability, str) and stability.strip():
            return stability

        kind = getattr(utterance, "kind", "archive_final")
        if kind == "live_final":
            return "medium"
        if kind in {"preview", "partial"}:
            return "low"
        return "final"

    payload = StreamPayloadResponse(
        session_id=session_id,
        input_source=input_source,
        utterances=[
            StreamUtteranceItemResponse(
                id=utterance.id,
                seq_num=utterance.seq_num,
                segment_id=getattr(
                    utterance,
                    "segment_id",
                    f"seg-{utterance.start_ms}-{utterance.end_ms}",
                ),
                text=utterance.text,
                confidence=utterance.confidence,
                start_ms=utterance.start_ms,
                end_ms=utterance.end_ms,
                is_partial=getattr(utterance, "kind", "archive_final") in {"preview", "partial", "live_final"},
                kind=getattr(utterance, "kind", "archive_final"),
                revision=getattr(utterance, "revision", None),
                input_source=(getattr(utterance, "input_source", None) or input_source),
                stability=resolve_stability(utterance),
            )
            for utterance in utterances
        ],
        events=[
            StreamEventItemResponse(
                id=event.id,
                type=event.event_type.value,
                title=event.title,
                evidence_text=event.evidence_text,
                state=event.state.value,
                source_utterance_id=event.source_utterance_id,
                speaker_label=event.speaker_label,
            )
            for event in events
        ],
    )
    return payload.model_dump()


def build_stream_error_payload(session_id: str, message: str) -> dict:
    """실시간 오류 응답을 공용 스키마로 직렬화한다."""

    payload = StreamPayloadResponse(
        session_id=session_id,
        utterances=[],
        events=[],
        error=message,
    )
    return payload.model_dump()
