"""이벤트/전사 데이터를 회의록 정본 문서로 매핑한다."""

from __future__ import annotations

from dataclasses import dataclass

from server.app.services.reports.audio.audio_postprocessing_service import (
    SpeakerTranscriptSegment,
)
from server.app.services.reports.composition.report_document import (
    ReportDocumentV1,
    ReportListItem,
)
from server.app.services.reports.composition.report_document_event_projection import (
    EVIDENCE_TEXT_LIMIT,
    LIST_TEXT_LIMIT,
    build_speaker_insights,
    clean_report_text,
    filter_report_events,
    infer_event_time_range,
    limit_report_text,
    to_action_item,
    to_event_candidate,
    to_list_item,
)
from server.app.services.reports.composition.report_metadata_projection import (
    build_report_metadata_fields,
    format_document_title,
    format_meeting_title,
)
from server.app.services.reports.composition.report_event_cleanup import (
    ReportEventCandidate,
    clean_events,
    group_events,
)
from server.app.services.reports.composition.report_session_context import (
    ReportSessionContext,
)
from server.app.services.reports.composition.speaker_event_projection_service import (
    SpeakerAttributedEvent,
)
from server.app.services.reports.composition.timeline_format import (
    format_timeline_range,
)

_TRANSCRIPT_EXCERPT_LIMIT = 12
_SUMMARY_TEXT_LIMIT = 220
_TRANSCRIPT_SEGMENT_TEXT_LIMIT = 180


@dataclass(frozen=True)
class _ReportEventGroups:
    cleaned: list[ReportEventCandidate]
    questions: list[ReportEventCandidate]
    decisions: list[ReportEventCandidate]
    action_items: list[ReportEventCandidate]
    risks: list[ReportEventCandidate]


def build_report_document_v1(
    *,
    session_id: str,
    events: list,
    speaker_transcript: list[SpeakerTranscriptSegment],
    speaker_events: list[SpeakerAttributedEvent],
    insight_source: str,
    session_context: ReportSessionContext | None = None,
) -> ReportDocumentV1:
    """실제 이벤트/전사 데이터를 고정 템플릿용 문서 구조로 변환한다."""

    context = session_context or ReportSessionContext(session_id=session_id)
    event_groups = _build_report_event_groups(events)

    return ReportDocumentV1(
        title=format_document_title(context, session_id),
        metadata=tuple(
            build_report_metadata_fields(
                session_id=session_id,
                context=context,
                speaker_transcript=speaker_transcript,
            )
        ),
        summary=tuple(
            _build_summary_items(
                context=context,
                session_id=session_id,
                questions=event_groups.questions,
                decisions=event_groups.decisions,
                action_items=event_groups.action_items,
                risks=event_groups.risks,
                transcript_count=len(speaker_transcript),
            )
        ),
        agenda=tuple(
            _build_agenda_items(
                context=context,
                session_id=session_id,
                events=event_groups.cleaned,
                speaker_transcript=speaker_transcript,
            )
        ),
        decisions=tuple(
            to_list_item(event, speaker_transcript) for event in event_groups.decisions
        ),
        action_items=tuple(
            to_action_item(event, speaker_transcript) for event in event_groups.action_items
        ),
        questions=tuple(
            to_list_item(event, speaker_transcript) for event in event_groups.questions
        ),
        risks=tuple(
            to_list_item(event, speaker_transcript) for event in event_groups.risks
        ),
        transcript_excerpt=tuple(_build_transcript_excerpt(speaker_transcript)),
        speaker_insights=tuple(build_speaker_insights(speaker_events)),
    )


def _build_report_event_groups(events: list) -> _ReportEventGroups:
    cleaned_events = filter_report_events(
        clean_events([to_event_candidate(event) for event in events])
    )
    grouped_events = group_events(cleaned_events)
    return _ReportEventGroups(
        cleaned=cleaned_events,
        questions=grouped_events["question"],
        decisions=grouped_events["decision"],
        action_items=grouped_events["action_item"],
        risks=grouped_events["risk"],
    )


def _build_summary_items(
    *,
    context: ReportSessionContext,
    session_id: str,
    questions: list[ReportEventCandidate],
    decisions: list[ReportEventCandidate],
    action_items: list[ReportEventCandidate],
    risks: list[ReportEventCandidate],
    transcript_count: int,
) -> list[str]:
    total_events = len(questions) + len(decisions) + len(action_items) + len(risks)
    topic = format_meeting_title(context, session_id) or "이 회의"
    if total_events == 0:
        return [f"{topic} 내용을 전사 {transcript_count}개 구간 기준으로 정리했습니다."]

    summary_items = [
        (
            f"{topic}에서 질문 {len(questions)}건, 결정 사항 {len(decisions)}건, "
        f"향후일정 {len(action_items)}건, 리스크 {len(risks)}건을 정리했습니다."
        )
    ]
    if decisions:
        summary_items.append(
            f"핵심 결정: {limit_report_text(decisions[0].title, _SUMMARY_TEXT_LIMIT)}"
        )
    if action_items:
        summary_items.append(
            f"우선 향후일정: {limit_report_text(action_items[0].title, _SUMMARY_TEXT_LIMIT)}"
        )
    if risks:
        summary_items.append(
            f"주요 리스크: {limit_report_text(risks[0].title, _SUMMARY_TEXT_LIMIT)}"
        )
    return summary_items


def _build_agenda_items(
    *,
    context: ReportSessionContext,
    session_id: str,
    events: list[ReportEventCandidate],
    speaker_transcript: list[SpeakerTranscriptSegment],
) -> list[ReportListItem]:
    meeting_title = format_meeting_title(context, session_id)
    if meeting_title:
        return [ReportListItem(limit_report_text(meeting_title, LIST_TEXT_LIMIT) or meeting_title)]

    topic_events = [event for event in events if event.event_type == "topic"]
    if topic_events:
        topic = topic_events[0]
        return [
            ReportListItem(
                text=limit_report_text(topic.title, LIST_TEXT_LIMIT) or "",
                speaker=topic.speaker_label,
                evidence=limit_report_text(topic.evidence_text, EVIDENCE_TEXT_LIMIT),
                time_range=infer_event_time_range(topic, speaker_transcript),
            )
        ]

    if not events:
        return [
            ReportListItem(
                "전사 내용을 기준으로 회의 주제를 검토했습니다.",
                evidence=f"전사 {len(speaker_transcript)}개 구간",
            )
        ]

    primary_event = events[0]
    return [
        ReportListItem(
            text=limit_report_text(_derive_agenda_title(primary_event.title), LIST_TEXT_LIMIT)
            or "",
            speaker=primary_event.speaker_label,
            evidence=limit_report_text(primary_event.evidence_text, EVIDENCE_TEXT_LIMIT),
            time_range=infer_event_time_range(primary_event, speaker_transcript),
        )
    ]


def _derive_agenda_title(value: str) -> str:
    text = clean_report_text(value)
    for suffix in (
        "을 논의한다.",
        "를 논의한다.",
        "을 검토한다.",
        "를 검토한다.",
        "을 확인한다.",
        "를 확인한다.",
    ):
        if text.endswith(suffix):
            return text[: -len(suffix)]
    return text


def _build_transcript_excerpt(
    speaker_transcript: list[SpeakerTranscriptSegment],
) -> list[str]:
    excerpt = [
        _format_transcript_segment(segment)
        for segment in speaker_transcript[:_TRANSCRIPT_EXCERPT_LIMIT]
        if segment.text.strip()
    ]
    remaining_count = len(speaker_transcript) - _TRANSCRIPT_EXCERPT_LIMIT
    if remaining_count > 0:
        excerpt.append(f"... 외 {remaining_count}개 구간")
    return excerpt


def _format_transcript_segment(segment: SpeakerTranscriptSegment) -> str:
    return (
        f"[{segment.speaker_label}] "
        f"{format_timeline_range(segment.start_ms, segment.end_ms)} "
        f"{limit_report_text(segment.text, _TRANSCRIPT_SEGMENT_TEXT_LIMIT)}"
    )
