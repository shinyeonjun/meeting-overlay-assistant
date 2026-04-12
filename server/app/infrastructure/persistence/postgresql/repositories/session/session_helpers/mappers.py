"""세션 저장소 모델 매핑 helper."""

from __future__ import annotations

from server.app.domain.participation import SessionParticipant
from server.app.domain.session import MeetingSession
from server.app.domain.shared.enums import AudioSource, SessionMode, SessionStatus
from server.app.infrastructure.persistence.postgresql.repositories._base import (
    parse_string_array,
)


def build_session_from_row(
    row,
    participant_links: tuple[SessionParticipant, ...],
) -> MeetingSession:
    """DB row를 MeetingSession으로 변환한다."""

    return MeetingSession(
        id=row["id"],
        title=row["title"],
        mode=SessionMode(row["mode"]),
        primary_input_source=row["primary_input_source"] or AudioSource.SYSTEM_AUDIO.value,
        status=SessionStatus(row["status"]),
        started_at=row["started_at"],
        created_by_user_id=row["created_by_user_id"],
        account_id=row["account_id"],
        contact_id=row["contact_id"],
        context_thread_id=row["context_thread_id"],
        ended_at=row["ended_at"],
        recording_artifact_id=(
            row["recording_artifact_id"] if "recording_artifact_id" in row else None
        ),
        post_processing_status=(
            row["post_processing_status"]
            if "post_processing_status" in row and row["post_processing_status"]
            else "not_started"
        ),
        post_processing_error_message=(
            row["post_processing_error_message"]
            if "post_processing_error_message" in row
            else None
        ),
        post_processing_requested_at=(
            row["post_processing_requested_at"]
            if "post_processing_requested_at" in row
            else None
        ),
        post_processing_started_at=(
            row["post_processing_started_at"]
            if "post_processing_started_at" in row
            else None
        ),
        post_processing_completed_at=(
            row["post_processing_completed_at"]
            if "post_processing_completed_at" in row
            else None
        ),
        canonical_transcript_version=(
            int(row["canonical_transcript_version"])
            if "canonical_transcript_version" in row and row["canonical_transcript_version"] is not None
            else 0
        ),
        canonical_events_version=(
            int(row["canonical_events_version"])
            if "canonical_events_version" in row and row["canonical_events_version"] is not None
            else 0
        ),
        actual_active_sources=tuple(parse_string_array(row["actual_active_sources"])),
        participant_links=participant_links,
    )


def rebuild_session(
    session: MeetingSession,
    participant_links: tuple[SessionParticipant, ...],
) -> MeetingSession:
    """저장 직후 participant 링크를 반영한 세션 객체를 다시 만든다."""

    return MeetingSession(
        id=session.id,
        title=session.title,
        mode=session.mode,
        primary_input_source=session.primary_input_source,
        status=session.status,
        started_at=session.started_at,
        created_by_user_id=session.created_by_user_id,
        account_id=session.account_id,
        contact_id=session.contact_id,
        context_thread_id=session.context_thread_id,
        ended_at=session.ended_at,
        recording_artifact_id=session.recording_artifact_id,
        post_processing_status=session.post_processing_status,
        post_processing_error_message=session.post_processing_error_message,
        post_processing_requested_at=session.post_processing_requested_at,
        post_processing_started_at=session.post_processing_started_at,
        post_processing_completed_at=session.post_processing_completed_at,
        canonical_transcript_version=session.canonical_transcript_version,
        canonical_events_version=session.canonical_events_version,
        actual_active_sources=session.actual_active_sources,
        participant_links=participant_links,
    )
