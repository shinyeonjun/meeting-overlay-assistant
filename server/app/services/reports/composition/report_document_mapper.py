"""이벤트/전사 데이터를 회의록 정본 문서로 매핑한다."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

from server.app.services.reports.audio.audio_postprocessing_service import (
    SpeakerTranscriptSegment,
)
from server.app.services.reports.composition.html_report_template import (
    ReportActionItem,
    ReportDocumentV1,
    ReportListItem,
    ReportMetaField,
)
from server.app.services.reports.composition.speaker_event_projection_service import (
    SpeakerAttributedEvent,
)
from server.app.services.reports.refinement.report_refiner import ReportRefinementEvent
from server.app.services.reports.refinement.structured_helpers.cleanup import (
    clean_events,
    clean_speaker_event_lines,
    group_events,
)

_TRANSCRIPT_EXCERPT_LIMIT = 12
_KST = ZoneInfo("Asia/Seoul")

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
    cleaned_events = clean_events([_to_refinement_event(event) for event in events])
    grouped_events = group_events(cleaned_events)
    question_events = grouped_events["question"]
    decision_events = grouped_events["decision"]
    action_events = grouped_events["action_item"]
    risk_events = grouped_events["risk"]

    return ReportDocumentV1(
        metadata=tuple(
            _build_metadata_fields(
                session_id=session_id,
                context=context,
                insight_source=insight_source,
                event_count=len(cleaned_events),
                transcript_count=len(speaker_transcript),
                question_count=len(question_events),
                decision_count=len(decision_events),
                action_count=len(action_events),
                risk_count=len(risk_events),
                speaker_transcript=speaker_transcript,
            )
        ),
        summary=tuple(
            _build_summary_items(
                questions=question_events,
                decisions=decision_events,
                action_items=action_events,
                risks=risk_events,
                transcript_count=len(speaker_transcript),
            )
        ),
        decisions=tuple(_to_list_item(event) for event in decision_events),
        action_items=tuple(_to_action_item(event) for event in action_events),
        questions=tuple(_to_list_item(event) for event in question_events),
        risks=tuple(_to_list_item(event) for event in risk_events),
        transcript_excerpt=tuple(_build_transcript_excerpt(speaker_transcript)),
        speaker_insights=tuple(_build_speaker_insights(speaker_events)),
    )


def render_report_markdown(
    *,
    session_id: str,
    document: ReportDocumentV1,
) -> str:
    """ReportDocumentV1을 기존 API가 쓰는 Markdown 리포트 형식으로 렌더링한다."""

    lines = [
        "# 회의 리포트",
        "",
        f"- 세션 ID: {session_id}",
        "",
        "## 회의 개요",
    ]
    _append_overview(lines, document)
    _append_list_section(lines, "질문", document.questions)
    _append_list_section(lines, "결정 사항", document.decisions, numbered=True)
    _append_action_section(lines, document.action_items)
    _append_list_section(lines, "리스크", document.risks)
    _append_text_section(lines, "참고 전사", document.transcript_excerpt)
    _append_text_section(lines, "발화자 기반 인사이트", document.speaker_insights)
    return "\n".join(lines)


def _to_refinement_event(event) -> ReportRefinementEvent:
    return ReportRefinementEvent(
        event_type=_value_of(event.event_type),
        title=event.title,
        state=_value_of(event.state),
        evidence_text=event.evidence_text,
        speaker_label=event.speaker_label,
        input_source=event.input_source,
    )


def _to_list_item(event: ReportRefinementEvent) -> ReportListItem:
    return ReportListItem(
        text=event.title,
        speaker=event.speaker_label,
        evidence=event.evidence_text,
    )


def _to_action_item(event: ReportRefinementEvent) -> ReportActionItem:
    return ReportActionItem(
        task=event.title,
        owner=event.speaker_label or "-",
        status=_format_state(event.state),
        note=event.evidence_text,
    )


def _build_metadata_fields(
    *,
    session_id: str,
    context: ReportSessionContext,
    insight_source: str,
    event_count: int,
    transcript_count: int,
    question_count: int,
    decision_count: int,
    action_count: int,
    risk_count: int,
    speaker_transcript: list[SpeakerTranscriptSegment],
) -> list[ReportMetaField]:
    return [
        ReportMetaField("회의일자", _format_meeting_date(context)),
        ReportMetaField("회의시간", _format_meeting_time(context)),
        ReportMetaField("회의장소", "미기록"),
        ReportMetaField("회의주제", _format_meeting_title(context, session_id)),
        ReportMetaField("회의안건", "자동 생성 회의록 검토"),
        ReportMetaField("참석자", _format_participants(context, speaker_transcript)),
        ReportMetaField("입력소스", _format_input_sources(context)),
        ReportMetaField("인사이트 출처", _format_insight_source(insight_source)),
        ReportMetaField("전사 구간", f"{transcript_count}건"),
        ReportMetaField("추출 이벤트", f"{event_count}건"),
        ReportMetaField("질문", f"{question_count}건"),
        ReportMetaField("의결사항", f"{decision_count}건"),
        ReportMetaField("액션 아이템", f"{action_count}건"),
        ReportMetaField("리스크", f"{risk_count}건"),
        ReportMetaField("세션 ID", session_id),
    ]


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


def _clean_text(value: str | None) -> str:
    return " ".join(value.strip().split()) if value else ""


def _build_summary_items(
    *,
    questions: list[ReportRefinementEvent],
    decisions: list[ReportRefinementEvent],
    action_items: list[ReportRefinementEvent],
    risks: list[ReportRefinementEvent],
    transcript_count: int,
) -> list[str]:
    total_events = len(questions) + len(decisions) + len(action_items) + len(risks)
    if total_events == 0:
        return [f"전사 {transcript_count}개 구간을 기준으로 회의 내용을 정리했습니다."]

    summary_items = [
        (
            f"질문 {len(questions)}건, 의결사항 {len(decisions)}건, "
            f"액션 아이템 {len(action_items)}건, 리스크 {len(risks)}건을 정리했습니다."
        )
    ]
    if decisions:
        summary_items.append(f"주요 의결사항: {decisions[0].title}")
    if action_items:
        summary_items.append(f"주요 후속 작업: {action_items[0].title}")
    if risks:
        summary_items.append(f"주요 리스크: {risks[0].title}")
    return summary_items


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


def _append_overview(lines: list[str], document: ReportDocumentV1) -> None:
    for label in (
        "회의일자",
        "회의시간",
        "회의주제",
        "참석자",
        "인사이트 출처",
        "전사 구간",
        "추출 이벤트",
        "질문",
        "의결사항",
        "액션 아이템",
        "리스크",
    ):
        value = _metadata_value(document.metadata, label)
        if value:
            lines.append(f"- {label}: {value}")
    for item in document.summary:
        lines.append(f"- {item}")


def _append_list_section(
    lines: list[str],
    heading: str,
    items: tuple[ReportListItem, ...],
    *,
    numbered: bool = False,
) -> None:
    lines.extend(["", f"## {heading}"])
    if not items:
        lines.append("- 없음")
        return

    for index, item in enumerate(items, start=1):
        prefix = f"{index}." if numbered else "-"
        lines.append(f"{prefix} {item.text}")
        lines.extend(_build_item_metadata_lines(item))


def _append_action_section(
    lines: list[str],
    items: tuple[ReportActionItem, ...],
) -> None:
    lines.extend(["", "## 액션 아이템"])
    if not items:
        lines.append("- 없음")
        return

    for item in items:
        checkbox = "x" if item.status in {"완료", "해결"} else " "
        lines.append(f"- [{checkbox}] {item.task}")
        if item.owner and item.owner != "-":
            lines.append(f"  - 담당자: {item.owner}")
        if item.due_date and item.due_date != "-":
            lines.append(f"  - 기한: {item.due_date}")
        if item.note:
            lines.append(f"  - 근거: {item.note}")


def _append_text_section(
    lines: list[str],
    heading: str,
    items: tuple[str, ...],
) -> None:
    lines.extend(["", f"## {heading}"])
    if not items:
        lines.append("- 없음")
        return
    lines.extend(f"- {item}" for item in items)


def _build_item_metadata_lines(item: ReportListItem) -> list[str]:
    metadata_lines: list[str] = []
    if item.speaker:
        metadata_lines.append(f"  - 발화자: {item.speaker}")
    if item.evidence:
        metadata_lines.append(f"  - 근거: {item.evidence}")
    return metadata_lines


def _metadata_value(fields: tuple[ReportMetaField, ...], label: str) -> str | None:
    for field in fields:
        if field.label == label:
            return field.value
    return None


def _format_transcript_segment(segment: SpeakerTranscriptSegment) -> str:
    return (
        f"[{segment.speaker_label}] "
        f"{_format_timeline_range(segment.start_ms, segment.end_ms)} "
        f"{segment.text}"
    )


def _format_timeline_range(start_ms: int, end_ms: int) -> str:
    return f"{_format_mmss(start_ms)}-{_format_mmss(end_ms)}"


def _format_mmss(value_ms: int) -> str:
    total_seconds = max(int(value_ms // 1000), 0)
    minutes, seconds = divmod(total_seconds, 60)
    return f"{minutes:02d}:{seconds:02d}"


def _format_state(state: str) -> str:
    return _STATE_LABELS.get(state, state)


def _format_insight_source(insight_source: str) -> str:
    return _INSIGHT_SOURCE_LABELS.get(insight_source, insight_source)


def _value_of(value) -> str:
    return str(getattr(value, "value", value))
