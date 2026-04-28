"""이벤트/전사 데이터를 회의록 정본 문서로 매핑한다."""

from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import datetime, timedelta, timezone
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
_SUMMARY_TEXT_LIMIT = 220
_LIST_TEXT_LIMIT = 180
_EVIDENCE_TEXT_LIMIT = 160
_ACTION_TASK_LIMIT = 140
_TRANSCRIPT_SEGMENT_TEXT_LIMIT = 180
_SPEAKER_INSIGHT_TEXT_LIMIT = 180
_KST = ZoneInfo("Asia/Seoul")

_EVENT_TYPE_LABELS = {
    "question": "질문",
    "decision": "결정",
    "action_item": "향후일정",
    "risk": "리스크",
}

_ACTIONABLE_TOKENS = (
    "정리",
    "준비",
    "공유",
    "확인",
    "검토",
    "작성",
    "수정",
    "추가",
    "업데이트",
    "배포",
    "테스트",
    "진행",
    "담당",
    "완료",
    "해야",
    "하겠습니다",
    "해주세요",
    "하기",
    "하기로",
    "만들",
    "보내",
    "올려",
    "체크리스트",
)


@dataclass(frozen=True)
class ReportSessionContext:
    """회의록 템플릿에 매핑할 세션 메타데이터."""

    session_id: str
    title: str | None = None
    started_at: str | None = None
    ended_at: str | None = None
    participants: tuple[str, ...] = ()
    organizer: str | None = None
    primary_input_source: str | None = None
    actual_active_sources: tuple[str, ...] = ()
    recording_file_modified_at: str | None = None
    recording_duration_ms: int | None = None

    @classmethod
    def from_session(cls, session) -> "ReportSessionContext":
        """MeetingSession 또는 동일 속성을 가진 객체에서 context를 만든다."""

        return cls(
            session_id=str(getattr(session, "id", "")),
            title=getattr(session, "title", None),
            started_at=getattr(session, "started_at", None),
            ended_at=getattr(session, "ended_at", None),
            participants=tuple(getattr(session, "participants", ()) or ()),
            organizer=(
                getattr(session, "organizer", None)
                or getattr(session, "host", None)
                or getattr(session, "created_by", None)
            ),
            primary_input_source=getattr(session, "primary_input_source", None),
            actual_active_sources=tuple(
                getattr(session, "actual_active_sources", ()) or ()
            ),
        )

    def with_recording_metadata(
        self,
        *,
        recording_file_modified_at: str | None,
        recording_duration_ms: int | None,
    ) -> "ReportSessionContext":
        return replace(
            self,
            recording_file_modified_at=recording_file_modified_at,
            recording_duration_ms=recording_duration_ms,
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
    cleaned_events = _filter_report_events(
        clean_events([_to_event_candidate(event) for event in events])
    )
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
        agenda=tuple(
            _build_agenda_items(
                context=context,
                session_id=session_id,
                events=cleaned_events,
                speaker_transcript=speaker_transcript,
            )
        ),
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
        text=_limit_text(event.title, _LIST_TEXT_LIMIT) or "",
        speaker=event.speaker_label,
        evidence=_limit_text(event.evidence_text, _EVIDENCE_TEXT_LIMIT),
        time_range=_infer_event_time_range(event, speaker_transcript),
    )


def _to_action_item(
    event: ReportEventCandidate,
    speaker_transcript: list[SpeakerTranscriptSegment],
) -> ReportActionItem:
    return ReportActionItem(
        task=_limit_text(event.title, _ACTION_TASK_LIMIT) or "",
        owner="",
        status="",
        note=_limit_text(event.evidence_text, _EVIDENCE_TEXT_LIMIT),
        time_range=_infer_event_time_range(event, speaker_transcript),
    )


def _build_metadata_fields(
    *,
    session_id: str,
    context: ReportSessionContext,
    speaker_transcript: list[SpeakerTranscriptSegment],
) -> list[ReportMetaField]:
    return [
        ReportMetaField("회의제목", _format_meeting_title(context, session_id)),
        ReportMetaField("일시", _format_meeting_datetime(context, speaker_transcript)),
        ReportMetaField("장소", ""),
        ReportMetaField("작성자", _format_organizer(context)),
        ReportMetaField("작성일", _format_meeting_date(context, speaker_transcript)),
        ReportMetaField("참석자", _format_participants(context, speaker_transcript)),
        ReportMetaField("회의 주최자", _format_organizer(context)),
    ]


def _format_document_title(context: ReportSessionContext, session_id: str) -> str:
    title = _format_meeting_title(context, session_id)
    return title or "회의록"


def _format_meeting_title(context: ReportSessionContext, session_id: str) -> str:
    del session_id
    if context.title and context.title.strip():
        return context.title.strip()
    return ""


def _format_meeting_date(
    context: ReportSessionContext,
    speaker_transcript: list[SpeakerTranscriptSegment] | None = None,
) -> str:
    started_at, ended_at = _resolve_meeting_time_bounds(
        context,
        speaker_transcript or [],
    )
    timestamp = started_at or ended_at
    if timestamp is None:
        return ""
    return timestamp.strftime("%Y-%m-%d")


def _format_meeting_time(
    context: ReportSessionContext,
    speaker_transcript: list[SpeakerTranscriptSegment] | None = None,
) -> str:
    started_at, ended_at = _resolve_meeting_time_bounds(
        context,
        speaker_transcript or [],
    )
    if started_at is None and ended_at is None:
        return ""
    if started_at is None:
        return _format_clock(ended_at, include_seconds=False)
    if ended_at is None:
        return _format_clock(started_at, include_seconds=False)
    include_seconds = _should_include_seconds(started_at, ended_at)
    if started_at.date() == ended_at.date():
        return (
            f"{_format_clock(started_at, include_seconds=include_seconds)} - "
            f"{_format_clock(ended_at, include_seconds=include_seconds)}"
        )
    return (
        f"{started_at:%m-%d} {_format_clock(started_at, include_seconds=include_seconds)} - "
        f"{ended_at:%m-%d} {_format_clock(ended_at, include_seconds=include_seconds)}"
    )


def _format_meeting_datetime(
    context: ReportSessionContext,
    speaker_transcript: list[SpeakerTranscriptSegment] | None = None,
) -> str:
    speaker_transcript = speaker_transcript or []
    meeting_date = _format_meeting_date(context, speaker_transcript)
    meeting_time = _format_meeting_time(context, speaker_transcript)
    if not meeting_date and not meeting_time:
        return ""
    if not meeting_date:
        return meeting_time
    if not meeting_time:
        return meeting_date
    return f"{meeting_date} {meeting_time}"


def _resolve_meeting_time_bounds(
    context: ReportSessionContext,
    speaker_transcript: list[SpeakerTranscriptSegment],
) -> tuple[datetime | None, datetime | None]:
    started_at = _parse_datetime(context.started_at)
    ended_at = _parse_datetime(context.ended_at)
    duration_ms = _resolve_recording_duration_ms(context, speaker_transcript)
    file_modified_at = _parse_datetime(context.recording_file_modified_at)

    if started_at is None and file_modified_at is not None:
        ended_at = ended_at or file_modified_at
        if duration_ms and duration_ms > 0:
            started_at = ended_at - timedelta(milliseconds=duration_ms)
        else:
            started_at = file_modified_at

    if started_at is not None and duration_ms and duration_ms > 0:
        duration_delta = timedelta(milliseconds=duration_ms)
        if _should_use_duration_based_end(started_at, ended_at, duration_delta):
            ended_at = started_at + duration_delta

    return started_at, ended_at


def _resolve_recording_duration_ms(
    context: ReportSessionContext,
    speaker_transcript: list[SpeakerTranscriptSegment],
) -> int | None:
    if context.recording_duration_ms and context.recording_duration_ms > 0:
        return context.recording_duration_ms
    if not speaker_transcript:
        return None
    return max((segment.end_ms for segment in speaker_transcript), default=0) or None


def _should_use_duration_based_end(
    started_at: datetime,
    ended_at: datetime | None,
    duration_delta: timedelta,
) -> bool:
    if ended_at is None or ended_at <= started_at:
        return True
    current_delta = ended_at - started_at
    tolerance = timedelta(seconds=5)
    return duration_delta > current_delta + tolerance


def _should_include_seconds(started_at: datetime, ended_at: datetime) -> bool:
    return (
        started_at.replace(second=0, microsecond=0)
        == ended_at.replace(second=0, microsecond=0)
    )


def _format_clock(value: datetime, *, include_seconds: bool) -> str:
    return value.strftime("%H:%M:%S" if include_seconds else "%H:%M")


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
    del speaker_transcript
    participants = [_clean_text(item) for item in context.participants]
    participants = [item for item in participants if item]
    return ", ".join(participants)


def _format_organizer(context: ReportSessionContext) -> str:
    organizer = _clean_text(context.organizer)
    return organizer


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
    topic = _format_meeting_title(context, session_id) or "이 회의"
    if total_events == 0:
        return [f"{topic} 내용을 전사 {transcript_count}개 구간 기준으로 정리했습니다."]

    summary_items = [
        (
            f"{topic}에서 질문 {len(questions)}건, 결정 사항 {len(decisions)}건, "
        f"향후일정 {len(action_items)}건, 리스크 {len(risks)}건을 정리했습니다."
        )
    ]
    if decisions:
        summary_items.append(f"핵심 결정: {_limit_text(decisions[0].title, _SUMMARY_TEXT_LIMIT)}")
    if action_items:
        summary_items.append(
            f"우선 향후일정: {_limit_text(action_items[0].title, _SUMMARY_TEXT_LIMIT)}"
        )
    if risks:
        summary_items.append(f"주요 리스크: {_limit_text(risks[0].title, _SUMMARY_TEXT_LIMIT)}")
    return summary_items


def _build_agenda_items(
    *,
    context: ReportSessionContext,
    session_id: str,
    events: list[ReportEventCandidate],
    speaker_transcript: list[SpeakerTranscriptSegment],
) -> list[ReportListItem]:
    meeting_title = _format_meeting_title(context, session_id)
    if meeting_title:
        return [ReportListItem(_limit_text(meeting_title, _LIST_TEXT_LIMIT) or meeting_title)]

    topic_events = [event for event in events if event.event_type == "topic"]
    if topic_events:
        topic = topic_events[0]
        return [
            ReportListItem(
                text=_limit_text(topic.title, _LIST_TEXT_LIMIT) or "",
                speaker=topic.speaker_label,
                evidence=_limit_text(topic.evidence_text, _EVIDENCE_TEXT_LIMIT),
                time_range=_infer_event_time_range(topic, speaker_transcript),
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
            text=_limit_text(_derive_agenda_title(primary_event.title), _LIST_TEXT_LIMIT) or "",
            speaker=primary_event.speaker_label,
            evidence=_limit_text(primary_event.evidence_text, _EVIDENCE_TEXT_LIMIT),
            time_range=_infer_event_time_range(primary_event, speaker_transcript),
        )
    ]


def _derive_agenda_title(value: str) -> str:
    text = _clean_text(value)
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


def _build_speaker_insights(
    speaker_events: list[SpeakerAttributedEvent],
) -> list[str]:
    return clean_speaker_event_lines(
        [
            _format_speaker_event(item)
            for item in speaker_events
            if _should_include_speaker_event(item)
        ]
    )


def _should_include_speaker_event(item: SpeakerAttributedEvent) -> bool:
    event = _to_event_candidate(item.event)
    return event.event_type != "action_item" or _looks_actionable(event)


def _format_speaker_event(item: SpeakerAttributedEvent) -> str:
    event = item.event
    title = _limit_text(event.title, _SPEAKER_INSIGHT_TEXT_LIMIT) or ""
    return f"[{_value_of(event.event_type)}] {item.speaker_label}: {title}"


def _format_transcript_segment(segment: SpeakerTranscriptSegment) -> str:
    return (
        f"[{segment.speaker_label}] "
        f"{format_timeline_range(segment.start_ms, segment.end_ms)} "
        f"{_limit_text(segment.text, _TRANSCRIPT_SEGMENT_TEXT_LIMIT)}"
    )


def _value_of(value) -> str:
    return str(getattr(value, "value", value))


def _filter_report_events(
    events: list[ReportEventCandidate],
) -> list[ReportEventCandidate]:
    """회의록에 바로 노출하기 애매한 오분류 액션 아이템을 제거한다."""

    return [
        event
        for event in events
        if event.event_type != "action_item" or _looks_actionable(event)
    ]


def _looks_actionable(event: ReportEventCandidate) -> bool:
    text = _clean_text(" ".join([event.title or "", event.evidence_text or ""]))
    if not text:
        return False
    if "?" in text:
        return False
    return any(token in text for token in _ACTIONABLE_TOKENS)


def _limit_text(value: str | None, limit: int) -> str | None:
    cleaned = _clean_text(value)
    if not cleaned:
        return None
    if len(cleaned) <= limit:
        return cleaned
    return f"{cleaned[: limit - 1].rstrip()}…"
