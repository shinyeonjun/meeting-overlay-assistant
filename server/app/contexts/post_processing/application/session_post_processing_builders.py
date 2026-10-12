"""session 후처리 결과로 canonical utterance와 meeting event를 만드는 순수 함수를 제공한다."""

from __future__ import annotations

from dataclasses import replace

from server.app.contexts.insight import MeetingAnalyzer, MeetingEvent
from server.app.core.clock import utc_now_epoch_ms as _now_ms
from server.app.domain.models.utterance import Utterance


def build_canonical_utterances(
    *,
    session_id: str,
    input_source: str,
    processing_job_id: str,
    speaker_transcript,
) -> list[Utterance]:
    """화자 전사 세그먼트를 canonical utterance 목록으로 바꾼다. 빈 텍스트는 건너뛴다."""

    utterances: list[Utterance] = []
    for index, segment in enumerate(speaker_transcript, start=1):
        text = segment.text.strip()
        if not text:
            continue
        utterances.append(
            Utterance.create(
                session_id=session_id,
                seq_num=index,
                start_ms=segment.start_ms,
                end_ms=segment.end_ms,
                text=text,
                confidence=segment.confidence,
                input_source=input_source,
                stt_backend="post_processed",
                latency_ms=None,
                speaker_label=segment.speaker_label,
                transcript_source="post_processed",
                processing_job_id=processing_job_id,
            )
        )
    return utterances


def build_canonical_events(
    *,
    analyzer: MeetingAnalyzer | None,
    utterances: list[Utterance],
    processing_job_id: str,
) -> list[MeetingEvent]:
    """canonical utterance마다 analyzer를 돌려 finalized event를 만든다. analyzer가 없으면 빈 목록이다."""

    if analyzer is None:
        return []

    finalized_at_ms = _now_ms()
    finalized_events: list[MeetingEvent] = []
    for utterance in utterances:
        for event in analyzer.analyze(utterance):
            finalized_events.append(
                replace(
                    event,
                    source_utterance_id=utterance.id,
                    evidence_text=event.evidence_text or utterance.text,
                    speaker_label=utterance.speaker_label or event.speaker_label,
                    input_source=utterance.input_source or event.input_source,
                    insight_scope="finalized",
                    event_source="post_processed",
                    processing_job_id=processing_job_id,
                    finalized_at_ms=finalized_at_ms,
                )
            )
    return finalized_events
