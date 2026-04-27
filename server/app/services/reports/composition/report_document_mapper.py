"""이벤트/전사 데이터를 회의록 정본 문서로 매핑한다."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

from server.app.services.reports.audio.audio_postprocessing_service import (
    SpeakerTranscriptSegment,
)
from server.app.services.reports.composition.report_document import (
    ReportActionItem,
    ReportDocumentV1,
    ReportListItem,
    ReportMetaField,
)
from server.app.services.reports.composition.report_event_cleanup import (
    ReportEventCandidate,
    clean_events,
    clean_speaker_event_lines,
    group_events,
)
from server.app.services.reports.composition.speaker_event_projection_service import (
    SpeakerAttributedEvent,
)
from server.app.services.reports.composition.timeline_format import (
    format_timeline_range,
)

_TRANSCRIPT_EXCERPT_LIMIT = 12
_AGENDA_EVENT_LIMIT = 8
_KST = ZoneInfo("Asia/Seoul")

_EVENT_TYPE_LABELS = {
    "question": "질문",
    "decision": "결정",
    "action_item": "후속 조치",
    "risk": "리스크",
}

_STATE_LABELS = {
    "open": "대기",
    "confirmed": "확정",
    "candidate": "후보",
    "answered": "답변됨",
    "unresolved": "미해결",
    "updated": "변경",
    "monitoring": "모니터링",
    "resolved": "해결",
    "closed": "완료",
    "active": "진행",
}

_INSIGHT_SOURCE_LABELS = {
    "high_precision_audio": "정식 후처리",
    "live_fallback": "라이브 이벤트",
}


@dataclass(frozen=True)
class ReportSessionContext:
    """회의록 템플릿에 매핑할 세션 메타데이터."""

    session_id: str
    title: str | None = None
    started_at: str | None = None
    ended_at: str | None = None
    participants: tuple[str, ...] = ()
    primary_input_source: str | None = None
    actual_active_sources: tuple[str, ...] = ()

    @classmethod
    def from_session(cls, session) -> "ReportSessionContext":
        """MeetingSession 또는 동일 속성을 가진 객체에서 context를 만든다."""

        return cls(
            session_id=str(getattr(session, "id", "")),
            title=getattr(session, "title", None),
            started_at=getattr(session, "started_at", None),
            ended_at=getattr(session, "ended_at", None),
            participants=tuple(getattr(session, "participants", ()) or ()),
            primary_input_source=getattr(session, "primary_input_source", None),
            actual_active_sources=tuple(
                getattr(session, "actual_active_sources", ()) or ()
            ),
        )


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
    cleaned_events = clean_events([_to_event_candidate(event) for event in events])
    grouped_events = group_events(cleaned_events)
    question_events = grouped_events["question"]
    decision_events = grouped_events["decision"]
    action_events = grouped_events["action_item"]
    risk_events = grouped_events["risk"]

    return ReportDocumentV1(
        title=_format_document_title(context, session_id),
        metadata=tuple(
            _build_metadata_fields(
                session_id=session_id,
                context=context,
                insight_source=insight_source,
                event_count=len(cleaned_events),
                transcript_count=len(speaker_transcript),
                speaker_transcript=speaker_transcript,
            )
        ),
        summary=tuple(
            _build_summary_items(
                context=context,
                session_id=session_id,
                questions=question_events,
                decisions=decision_events,
                action_items=action_events,
                risks=risk_events,
                transcript_count=len(speaker_transcript),
            )
        ),
        agenda=tuple(_build_agenda_items(cleaned_events, speaker_transcript)),
        decisions=tuple(
            _to_list_item(event, speaker_transcript) for event in decision_events
        ),
        action_items=tuple(
            _to_action_item(event, speaker_transcript) for event in action_events
        ),
        questions=tuple(
            _to_list_item(event, speaker_transcript) for event in question_events
        ),
        risks=tuple(
            _to_list_item(event, speaker_transcript) for event in risk_events
        ),
        transcript_excerpt=tuple(_build_transcript_excerpt(speaker_transcript)),
        speaker_insights=tuple(_build_speaker_insights(speaker_events)),
    )


def _to_event_candidate(event) -> ReportEventCandidate:
    return ReportEventCandidate(
        event_type=_value_of(event.event_type),
        title=event.title,
        state=_value_of(event.state),
        evidence_text=event.evidence_text,
        speaker_label=event.speaker_label,
        input_source=event.input_source,
    )


def _to_list_item(
    event: ReportEventCandidate,
    speaker_transcript: list[SpeakerTranscriptSegment],
) -> ReportListItem:
    return ReportListItem(
        text=event.title,
        speaker=event.speaker_label,
        evidence=event.evidence_text,
        time_range=_infer_event_time_range(event, speaker_transcript),
    )


def _to_action_item(
    event: ReportEventCandidate,
    speaker_transcript: list[SpeakerTranscriptSegment],
) -> ReportActionItem:
    return ReportActionItem(
        task=event.title,
        owner=event.speaker_label or "-",
        status=_format_state(event.state),
        note=event.evidence_text,
        time_range=_infer_event_time_range(event, speaker_transcript),
    )


def _build_metadata_fields(
    *,
    session_id: str,
    context: ReportSessionContext,
    insight_source: str,
    event_count: int,
    transcript_count: int,
    speaker_transcript: list[SpeakerTranscriptSegment],
) -> list[ReportMetaField]:
    return [
        ReportMetaField("회의일자", _format_meeting_date(context)),
        ReportMetaField("회의시간", _format_meeting_time(context)),
        ReportMetaField("회의장소", "미기록"),
        ReportMetaField("회의주제", _format_meeting_title(context, session_id)),
        ReportMetaField("참석자", _format_participants(context, speaker_transcript)),
        ReportMetaField(
            "기록 기준",
            _format_record_basis(
                context=context,
                insight_source=insight_source,
                transcript_count=transcript_count,
                event_count=event_count,
            ),
        ),
    ]


def _format_document_title(context: ReportSessionContext, session_id: str) -> str:
    title = _format_meeting_title(context, session_id)
    return title if title and not title.startswith("세션 ") else "회의 요약"


def _format_meeting_title(context: ReportSessionContext, session_id: str) -> str:
    if context.title and context.title.strip():
        return context.title.strip()
    return f"세션 {session_id}"


def _format_meeting_date(context: ReportSessionContext) -> str:
    timestamp = _parse_datetime(context.started_at) or _parse_datetime(context.ended_at)
    if timestamp is None:
        return "-"
    return timestamp.strftime("%Y-%m-%d")


def _format_meeting_time(context: ReportSessionContext) -> str:
    started_at = _parse_datetime(context.started_at)
    ended_at = _parse_datetime(context.ended_at)
    if started_at is None and ended_at is None:
        return "-"
    if started_at is None:
        return f"- {ended_at:%H:%M}"
    if ended_at is None:
        return f"{started_at:%H:%M} -"
    if started_at.date() == ended_at.date():
        return f"{started_at:%H:%M} - {ended_at:%H:%M}"
    return f"{started_at:%m-%d %H:%M} - {ended_at:%m-%d %H:%M}"


def _parse_datetime(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(_KST)


def _format_participants(
    context: ReportSessionContext,
    speaker_transcript: list[SpeakerTranscriptSegment],
) -> str:
    participants = [_clean_text(item) for item in context.participants]
    participants = [item for item in participants if item]
    if not participants:
        participants = _unique_speaker_labels(speaker_transcript)
    return ", ".join(participants) if participants else "-"


def _unique_speaker_labels(
    speaker_transcript: list[SpeakerTranscriptSegment],
) -> list[str]:
    labels: list[str] = []
    seen: set[str] = set()
    for segment in speaker_transcript:
        label = _clean_text(segment.speaker_label)
        if not label or label in seen:
            continue
        labels.append(label)
        seen.add(label)
    return labels


def _format_input_sources(context: ReportSessionContext) -> str:
    sources = [_clean_text(item) for item in context.actual_active_sources]
    sources = [item for item in sources if item]
    if not sources and context.primary_input_source:
        sources = [context.primary_input_source.strip()]
    return ", ".join(sources) if sources else "-"


def _format_record_basis(
    *,
    context: ReportSessionContext,
    insight_source: str,
    transcript_count: int,
    event_count: int,
) -> str:
    parts = [
        _format_insight_source(insight_source),
        f"전사 {transcript_count}개 구간",
        f"추출 이벤트 {event_count}건",
    ]
    input_sources = _format_input_sources(context)
    if input_sources != "-":
        parts.append(f"녹음 소스 {input_sources}")
    return " · ".join(parts)


def _infer_event_time_range(
    event: ReportEventCandidate,
    speaker_transcript: list[SpeakerTranscriptSegment],
) -> str | None:
    evidence = _clean_text(event.evidence_text)
    title = _clean_text(event.title)
    speaker_label = _clean_text(event.speaker_label)
    if not speaker_transcript or not (evidence or title):
        return None

    for segment in speaker_transcript:
        segment_text = _clean_text(segment.text)
        segment_speaker = _clean_text(segment.speaker_label)
        if speaker_label and segment_speaker and speaker_label != segment_speaker:
            continue
        if _text_matches_segment(evidence, segment_text) or _text_matches_segment(
            title,
            segment_text,
        ):
            return format_timeline_range(segment.start_ms, segment.end_ms)
    return None


def _text_matches_segment(candidate: str, segment_text: str) -> bool:
    if not candidate or not segment_text:
        return False
    if candidate in segment_text or segment_text in candidate:
        return True
    compact_candidate = candidate.replace(" ", "")
    compact_segment = segment_text.replace(" ", "")
    return compact_candidate in compact_segment or compact_segment in compact_candidate


def _clean_text(value: str | None) -> str:
    return " ".join(value.strip().split()) if value else ""


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
    topic = _format_meeting_title(context, session_id)
    if total_events == 0:
        return [f"{topic} 내용을 전사 {transcript_count}개 구간 기준으로 정리했습니다."]

    summary_items = [
        (
            f"{topic}에서 질문 {len(questions)}건, 결정 사항 {len(decisions)}건, "
            f"후속 조치 {len(action_items)}건, 리스크 {len(risks)}건을 정리했습니다."
        )
    ]
    if decisions:
        summary_items.append(f"핵심 결정: {decisions[0].title}")
    if action_items:
        summary_items.append(f"우선 후속 조치: {action_items[0].title}")
    if risks:
        summary_items.append(f"주요 리스크: {risks[0].title}")
    return summary_items


def _build_agenda_items(
    events: list[ReportEventCandidate],
    speaker_transcript: list[SpeakerTranscriptSegment],
) -> list[ReportListItem]:
    if not events:
        return [
            ReportListItem(
                "전사 내용을 기준으로 회의 흐름을 검토했습니다.",
                evidence=f"전사 {len(speaker_transcript)}개 구간",
            )
        ]

    agenda_items: list[ReportListItem] = []
    for event in events[:_AGENDA_EVENT_LIMIT]:
        event_type_label = _EVENT_TYPE_LABELS.get(event.event_type, event.event_type)
        agenda_items.append(
            ReportListItem(
                text=f"{event_type_label}: {event.title}",
                speaker=event.speaker_label,
                evidence=event.evidence_text,
                time_range=_infer_event_time_range(event, speaker_transcript),
            )
        )
    remaining_count = len(events) - _AGENDA_EVENT_LIMIT
    if remaining_count > 0:
        agenda_items.append(ReportListItem(f"외 {remaining_count}개 논의 항목"))
    return agenda_items


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


def _build_speaker_insights(
    speaker_events: list[SpeakerAttributedEvent],
) -> list[str]:
    return clean_speaker_event_lines(
        [_format_speaker_event(item) for item in speaker_events]
    )


def _format_speaker_event(item: SpeakerAttributedEvent) -> str:
    event = item.event
    return f"[{_value_of(event.event_type)}] {item.speaker_label}: {event.title}"


def _format_transcript_segment(segment: SpeakerTranscriptSegment) -> str:
    return (
        f"[{segment.speaker_label}] "
        f"{format_timeline_range(segment.start_ms, segment.end_ms)} "
        f"{segment.text}"
    )


def _format_state(state: str) -> str:
    return _STATE_LABELS.get(state, state)


def _format_insight_source(insight_source: str) -> str:
    return _INSIGHT_SOURCE_LABELS.get(insight_source, insight_source)


def _value_of(value) -> str:
    return str(getattr(value, "value", value))
