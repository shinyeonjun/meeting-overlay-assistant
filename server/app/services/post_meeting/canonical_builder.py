"""후처리 STT 결과를 canonical utterance/event로 변환한다."""

from __future__ import annotations

from dataclasses import replace

from server.app.domain.events import MeetingEvent
from server.app.domain.models.utterance import Utterance
from server.app.services.analysis.analyzers.analyzer import MeetingAnalyzer
from server.app.services.reports.audio.audio_postprocessing_service import (
    SpeakerTranscriptSegment,
)


def build_canonical_utterances(
    *,
    session_id: str,
    input_source: str,
    processing_job_id: str,
    speaker_transcript: list[SpeakerTranscriptSegment],
) -> list[Utterance]:
    """후처리 STT segment를 최종 canonical utterance로 변환한다."""

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
    utterances: list[Utterance],
    processing_job_id: str,
    analyzer: MeetingAnalyzer | None,
    finalized_at_ms: int,
) -> list[MeetingEvent]:
    """canonical utterance에 회의 분석기를 적용해 최종 event를 만든다."""

    if analyzer is None:
        return []

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
