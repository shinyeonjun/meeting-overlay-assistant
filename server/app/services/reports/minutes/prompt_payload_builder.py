"""회의록 AI 분석용 prompt payload 구성을 담당한다."""
from __future__ import annotations

import json

from server.app.services.reports.audio.audio_postprocessing_service import (
    SpeakerTranscriptSegment,
)
from server.app.services.reports.composition.report_session_context import (
    ReportSessionContext,
)
from server.app.services.reports.composition.timeline_format import (
    format_timeline_range,
)
from server.app.services.reports.minutes.normalization import (
    clean_text as _clean_text,
    value_of as _value_of,
)


class MeetingMinutesPromptPayloadMixin:
    """회의록 분석 prompt에 들어갈 context/event/transcript payload를 만든다."""

    def _build_prompt(
        self,
        *,
        session_id: str,
        session_context: ReportSessionContext | None,
        speaker_transcript: list[SpeakerTranscriptSegment],
        events: list,
        analysis_scope: str = "full",
    ) -> str:
        payload = {
            "session_id": session_id,
            "analysis_scope": analysis_scope,
            "분석 범위 안내": _build_scope_instruction(analysis_scope),
            "회의 메타데이터": _build_context_payload(session_context),
            "작성할 필드": [
                "agenda",
                "overview",
                "sections.title",
                "sections.background",
                "sections.opinions",
                "sections.review",
                "sections.direction",
                "sections.*.important_phrases",
                "decisions",
                "special_notes",
                "follow_up",
            ],
            "이벤트 후보": _build_event_candidates(
                events,
                limit=self._config.max_event_candidates,
            ),
            "STT 전사": self._build_transcript_payload(speaker_transcript),
        }
        return json.dumps(payload, ensure_ascii=False, separators=(",", ":"))

    def _build_transcript_payload(
        self,
        speaker_transcript: list[SpeakerTranscriptSegment],
    ) -> list[dict[str, object]]:
        entries: list[dict[str, object]] = []
        total_chars = 0
        for segment in speaker_transcript:
            text = _clean_text(segment.text)
            if not text:
                continue
            entry = {
                "time_range": format_timeline_range(segment.start_ms, segment.end_ms),
                "speaker": segment.speaker_label,
                "text": text,
            }
            total_chars += len(text)
            if entries and total_chars > self._config.max_transcript_chars:
                entries.append(
                    {
                        "time_range": "-",
                        "speaker": "system",
                        "text": "전사가 길어 이후 일부 구간은 이번 AI 분석 입력에서 생략되었습니다.",
                    }
                )
                break
            entries.append(entry)
        return entries


def _build_context_payload(
    session_context: ReportSessionContext | None,
) -> dict[str, object]:
    if session_context is None:
        return {}
    return {
        "title": session_context.title,
        "started_at": session_context.started_at,
        "ended_at": session_context.ended_at,
        "participants": list(session_context.participants),
        "organizer": session_context.organizer,
        "primary_input_source": session_context.primary_input_source,
    }


def _build_scope_instruction(analysis_scope: str) -> str:
    if analysis_scope == "full":
        return "제공된 STT 전사 전체를 기준으로 회의록 payload를 작성한다."
    return (
        "긴 회의 전사의 일부 구간이다. 현재 구간에서 실제로 논의된 내용만 "
        "sections에 우선 정리하고, 최종 병합에서 전체 회의록으로 합친다."
    )


def _build_event_candidates(events: list, *, limit: int) -> list[dict[str, object]]:
    candidates = []
    for event in events[:limit]:
        candidates.append(
            {
                "event_type": _value_of(getattr(event, "event_type", "")),
                "title": getattr(event, "title", ""),
                "state": _value_of(getattr(event, "state", "")),
                "speaker": getattr(event, "speaker_label", None),
                "evidence": getattr(event, "evidence_text", None),
            }
        )
    return candidates


def _chunk_segments(
    speaker_transcript: list[SpeakerTranscriptSegment],
    *,
    max_segments: int,
) -> list[list[SpeakerTranscriptSegment]]:
    chunks: list[list[SpeakerTranscriptSegment]] = []
    current: list[SpeakerTranscriptSegment] = []
    for segment in speaker_transcript:
        if len(current) >= max_segments:
            chunks.append(current)
            current = []
        current.append(segment)
    if current:
        chunks.append(current)
    return chunks
