"""회의 이벤트를 ReportDocumentV1 하위 항목으로 변환하는 helper."""

from __future__ import annotations

from server.app.services.reports.audio.audio_postprocessing_service import (
    SpeakerTranscriptSegment,
)
from server.app.services.reports.composition.report_document import (
    ReportActionItem,
    ReportListItem,
)
from server.app.services.reports.composition.report_event_cleanup import (
    ReportEventCandidate,
    clean_speaker_event_lines,
)
from server.app.services.reports.composition.speaker_event_projection_service import (
    SpeakerAttributedEvent,
)
from server.app.services.reports.composition.timeline_format import (
    format_timeline_range,
)

LIST_TEXT_LIMIT = 180
EVIDENCE_TEXT_LIMIT = 160
ACTION_TASK_LIMIT = 140
SPEAKER_INSIGHT_TEXT_LIMIT = 180

ACTIONABLE_TOKENS = (
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


def to_event_candidate(event) -> ReportEventCandidate:
    return ReportEventCandidate(
        event_type=value_of(event.event_type),
        title=event.title,
        state=value_of(event.state),
        evidence_text=event.evidence_text,
        speaker_label=event.speaker_label,
        input_source=event.input_source,
    )


def to_list_item(
    event: ReportEventCandidate,
    speaker_transcript: list[SpeakerTranscriptSegment],
) -> ReportListItem:
    return ReportListItem(
        text=limit_report_text(event.title, LIST_TEXT_LIMIT) or "",
        speaker=event.speaker_label,
        evidence=limit_report_text(event.evidence_text, EVIDENCE_TEXT_LIMIT),
        time_range=infer_event_time_range(event, speaker_transcript),
    )


def to_action_item(
    event: ReportEventCandidate,
    speaker_transcript: list[SpeakerTranscriptSegment],
) -> ReportActionItem:
    return ReportActionItem(
        task=limit_report_text(event.title, ACTION_TASK_LIMIT) or "",
        owner="",
        status="",
        note=limit_report_text(event.evidence_text, EVIDENCE_TEXT_LIMIT),
        time_range=infer_event_time_range(event, speaker_transcript),
    )


def infer_event_time_range(
    event: ReportEventCandidate,
    speaker_transcript: list[SpeakerTranscriptSegment],
) -> str | None:
    evidence = clean_report_text(event.evidence_text)
    title = clean_report_text(event.title)
    speaker_label = clean_report_text(event.speaker_label)
    if not speaker_transcript or not (evidence or title):
        return None

    for segment in speaker_transcript:
        segment_text = clean_report_text(segment.text)
        segment_speaker = clean_report_text(segment.speaker_label)
        if speaker_label and segment_speaker and speaker_label != segment_speaker:
            continue
        if _text_matches_segment(evidence, segment_text) or _text_matches_segment(
            title,
            segment_text,
        ):
            return format_timeline_range(segment.start_ms, segment.end_ms)
    return None


def filter_report_events(
    events: list[ReportEventCandidate],
) -> list[ReportEventCandidate]:
    """회의록에 바로 노출하기 애매한 오분류 액션 아이템을 제거한다."""

    return [
        event
        for event in events
        if event.event_type != "action_item" or looks_actionable(event)
    ]


def build_speaker_insights(
    speaker_events: list[SpeakerAttributedEvent],
) -> list[str]:
    return clean_speaker_event_lines(
        [
            _format_speaker_event(item)
            for item in speaker_events
            if _should_include_speaker_event(item)
        ]
    )


def looks_actionable(event: ReportEventCandidate) -> bool:
    text = clean_report_text(" ".join([event.title or "", event.evidence_text or ""]))
    if not text:
        return False
    if "?" in text:
        return False
    return any(token in text for token in ACTIONABLE_TOKENS)


def limit_report_text(value: str | None, limit: int) -> str | None:
    cleaned = clean_report_text(value)
    if not cleaned:
        return None
    if len(cleaned) <= limit:
        return cleaned
    return f"{cleaned[: limit - 1].rstrip()}…"


def clean_report_text(value: str | None) -> str:
    return " ".join(value.strip().split()) if value else ""


def value_of(value) -> str:
    return str(getattr(value, "value", value))


def _text_matches_segment(candidate: str, segment_text: str) -> bool:
    if not candidate or not segment_text:
        return False
    if candidate in segment_text or segment_text in candidate:
        return True
    compact_candidate = candidate.replace(" ", "")
    compact_segment = segment_text.replace(" ", "")
    return compact_candidate in compact_segment or compact_segment in compact_candidate


def _should_include_speaker_event(item: SpeakerAttributedEvent) -> bool:
    event = to_event_candidate(item.event)
    return event.event_type != "action_item" or looks_actionable(event)


def _format_speaker_event(item: SpeakerAttributedEvent) -> str:
    event = item.event
    title = limit_report_text(event.title, SPEAKER_INSIGHT_TEXT_LIMIT) or ""
    return f"[{value_of(event.event_type)}] {item.speaker_label}: {title}"
