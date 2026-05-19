"""회의록 문서의 메타데이터 필드를 구성한다."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

from server.app.services.reports.audio.audio_postprocessing_service import (
    SpeakerTranscriptSegment,
)
from server.app.services.reports.composition.report_document import ReportMetaField
from server.app.services.reports.composition.report_session_context import (
    ReportSessionContext,
)


_KST = ZoneInfo("Asia/Seoul")


def build_report_metadata_fields(
    *,
    session_id: str,
    context: ReportSessionContext,
    speaker_transcript: list[SpeakerTranscriptSegment],
) -> list[ReportMetaField]:
    return [
        ReportMetaField("회의제목", format_meeting_title(context, session_id)),
        ReportMetaField("일시", format_meeting_datetime(context, speaker_transcript)),
        ReportMetaField("장소", ""),
        ReportMetaField("작성자", format_organizer(context)),
        ReportMetaField("작성일", format_meeting_date(context, speaker_transcript)),
        ReportMetaField("참석자", format_participants(context, speaker_transcript)),
        ReportMetaField("회의 주최자", format_organizer(context)),
    ]


def format_document_title(context: ReportSessionContext, session_id: str) -> str:
    title = format_meeting_title(context, session_id)
    return title or "회의록"


def format_meeting_title(context: ReportSessionContext, session_id: str) -> str:
    del session_id
    if context.title and context.title.strip():
        return context.title.strip()
    return ""


def format_meeting_date(
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


def format_meeting_time(
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


def format_meeting_datetime(
    context: ReportSessionContext,
    speaker_transcript: list[SpeakerTranscriptSegment] | None = None,
) -> str:
    speaker_transcript = speaker_transcript or []
    meeting_date = format_meeting_date(context, speaker_transcript)
    meeting_time = format_meeting_time(context, speaker_transcript)
    if not meeting_date and not meeting_time:
        return ""
    if not meeting_date:
        return meeting_time
    if not meeting_time:
        return meeting_date
    return f"{meeting_date} {meeting_time}"


def format_participants(
    context: ReportSessionContext,
    speaker_transcript: list[SpeakerTranscriptSegment],
) -> str:
    del speaker_transcript
    participants = [_clean_text(item) for item in context.participants]
    participants = [item for item in participants if item]
    return ", ".join(participants)


def format_organizer(context: ReportSessionContext) -> str:
    return _clean_text(context.organizer)


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


def _clean_text(value: str | None) -> str:
    return " ".join(value.strip().split()) if value else ""
