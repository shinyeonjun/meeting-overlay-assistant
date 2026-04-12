"""세션 저장소 SQL 실행 helper."""

from __future__ import annotations

from server.app.domain.participation import SessionParticipant
from server.app.domain.session import MeetingSession
from server.app.domain.shared.enums import SessionStatus
from server.app.infrastructure.persistence.postgresql.repositories._base import (
    to_jsonb_parameter,
)


def upsert_session(connection, session: MeetingSession) -> None:
    """세션 row를 upsert한다."""

    connection.execute(
        """
        INSERT INTO sessions (
            id,
            title,
            mode,
            created_by_user_id,
            account_id,
            contact_id,
            context_thread_id,
            primary_input_source,
            actual_active_sources,
            started_at,
            ended_at,
            recovery_required,
            recovery_reason,
            recovery_detected_at,
            status,
            recording_artifact_id,
            post_processing_status,
            post_processing_error_message,
            post_processing_requested_at,
            post_processing_started_at,
            post_processing_completed_at,
            canonical_transcript_version,
            canonical_events_version
        )
        VALUES (
            %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
        )
        ON CONFLICT (id) DO UPDATE SET
            title = EXCLUDED.title,
            mode = EXCLUDED.mode,
            created_by_user_id = EXCLUDED.created_by_user_id,
            account_id = EXCLUDED.account_id,
            contact_id = EXCLUDED.contact_id,
            context_thread_id = EXCLUDED.context_thread_id,
            primary_input_source = EXCLUDED.primary_input_source,
            actual_active_sources = EXCLUDED.actual_active_sources,
            started_at = EXCLUDED.started_at,
            ended_at = EXCLUDED.ended_at,
            recovery_required = EXCLUDED.recovery_required,
            recovery_reason = EXCLUDED.recovery_reason,
            recovery_detected_at = EXCLUDED.recovery_detected_at,
            status = EXCLUDED.status,
            recording_artifact_id = EXCLUDED.recording_artifact_id,
            post_processing_status = EXCLUDED.post_processing_status,
            post_processing_error_message = EXCLUDED.post_processing_error_message,
            post_processing_requested_at = EXCLUDED.post_processing_requested_at,
            post_processing_started_at = EXCLUDED.post_processing_started_at,
            post_processing_completed_at = EXCLUDED.post_processing_completed_at,
            canonical_transcript_version = EXCLUDED.canonical_transcript_version,
            canonical_events_version = EXCLUDED.canonical_events_version
        """,
        (
            session.id,
            session.title,
            session.mode.value,
            session.created_by_user_id,
            session.account_id,
            session.contact_id,
            session.context_thread_id,
            session.primary_input_source,
            to_jsonb_parameter(list(session.actual_active_sources)),
            session.started_at,
            session.ended_at,
            session.recovery_required,
            session.recovery_reason,
            session.recovery_detected_at,
            session.status.value,
            session.recording_artifact_id,
            session.post_processing_status,
            session.post_processing_error_message,
            session.post_processing_requested_at,
            session.post_processing_started_at,
            session.post_processing_completed_at,
            session.canonical_transcript_version,
            session.canonical_events_version,
        ),
    )


def replace_session_participants(
    connection,
    *,
    session_id: str,
    participant_links: tuple[SessionParticipant, ...],
) -> None:
    """세션 참여자 목록을 통째로 교체한다."""

    connection.execute(
        "DELETE FROM session_participants WHERE session_id = %s",
        (session_id,),
    )
    for index, participant in enumerate(participant_links):
        connection.execute(
            """
            INSERT INTO session_participants (
                session_id,
                participant_order,
                participant_name,
                normalized_participant_name,
                participant_email,
                participant_job_title,
                participant_department,
                resolution_status,
                contact_id,
                account_id
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """,
            (
                session_id,
                index,
                participant.name,
                participant.normalized_name,
                participant.email,
                participant.job_title,
                participant.department,
                participant.resolution_status,
                participant.contact_id,
                participant.account_id,
            ),
        )


def fetch_session_row(connection, session_id: str):
    """세션 한 건 row를 조회한다."""

    return connection.execute(
        "SELECT * FROM sessions WHERE id = %s",
        (session_id,),
    ).fetchone()


def fetch_running_session_rows(connection, *, limit: int = 500):
    """실행 중인 세션 row 목록을 조회한다."""

    return connection.execute(
        """
        SELECT *
        FROM sessions
        WHERE status = %s
        ORDER BY started_at ASC
        LIMIT %s
        """,
        (SessionStatus.RUNNING.value, limit),
    ).fetchall()


def mark_session_recovery_required_if_running(
    connection,
    *,
    session_id: str,
    recovery_reason: str,
    recovery_detected_at: str,
):
    """실행 중인 세션만 복구 필요 상태로 전이한다."""

    return connection.execute(
        """
        UPDATE sessions
        SET
            status = %s,
            ended_at = COALESCE(ended_at, %s),
            recovery_required = TRUE,
            recovery_reason = %s,
            recovery_detected_at = %s
        WHERE id = %s
          AND status = %s
        RETURNING *
        """,
        (
            SessionStatus.ENDED.value,
            recovery_detected_at,
            recovery_reason,
            recovery_detected_at,
            session_id,
            SessionStatus.RUNNING.value,
        ),
    ).fetchone()


def delete_session_row(connection, session_id: str) -> bool:
    """세션 row를 삭제한다."""

    row = connection.execute(
        "DELETE FROM sessions WHERE id = %s RETURNING id",
        (session_id,),
    ).fetchone()
    return row is not None


def fetch_recent_session_rows(
    connection,
    *,
    created_by_user_id: str | None = None,
    account_id: str | None = None,
    contact_id: str | None = None,
    context_thread_id: str | None = None,
    limit: int = 50,
):
    """조건에 맞는 최근 세션 row를 조회한다."""

    query = "SELECT * FROM sessions"
    params: list[object] = []
    conditions: list[str] = []

    if created_by_user_id is not None:
        conditions.append("created_by_user_id = %s")
        params.append(created_by_user_id)
    if account_id is not None:
        conditions.append("account_id = %s")
        params.append(account_id)
    if contact_id is not None:
        conditions.append("contact_id = %s")
        params.append(contact_id)
    if context_thread_id is not None:
        conditions.append("context_thread_id = %s")
        params.append(context_thread_id)

    if conditions:
        query += " WHERE " + " AND ".join(conditions)
    query += " ORDER BY started_at DESC NULLS LAST LIMIT %s"
    params.append(limit)

    return connection.execute(query, tuple(params)).fetchall()


def fetch_running_session_count(connection) -> int:
    """실행 중 세션 수를 조회한다."""

    row = connection.execute(
        "SELECT COUNT(*) AS total FROM sessions WHERE status = %s",
        (SessionStatus.RUNNING.value,),
    ).fetchone()
    return int(row["total"]) if row is not None else 0


def fetch_running_session_count_filtered(
    connection,
    *,
    created_by_user_id: str | None = None,
    account_id: str | None = None,
    contact_id: str | None = None,
    context_thread_id: str | None = None,
) -> int:
    """조건에 맞는 진행 중 세션 수를 조회한다."""

    query = "SELECT COUNT(*) AS total FROM sessions WHERE status = %s"
    params: list[object] = [SessionStatus.RUNNING.value]

    if created_by_user_id is not None:
        query += " AND created_by_user_id = %s"
        params.append(created_by_user_id)
    if account_id is not None:
        query += " AND account_id = %s"
        params.append(account_id)
    if contact_id is not None:
        query += " AND contact_id = %s"
        params.append(contact_id)
    if context_thread_id is not None:
        query += " AND context_thread_id = %s"
        params.append(context_thread_id)

    row = connection.execute(query, tuple(params)).fetchone()
    return int(row["total"]) if row is not None else 0


def list_session_participants(connection, session_id: str) -> tuple[SessionParticipant, ...]:
    """세션 참여자 목록을 조회한다."""

    rows = connection.execute(
        """
        SELECT
            participant_name,
            normalized_participant_name,
            participant_email,
            participant_job_title,
            participant_department,
            resolution_status,
            contact_id,
            account_id
        FROM session_participants
        WHERE session_id = %s
        ORDER BY participant_order ASC
        """,
        (session_id,),
    ).fetchall()
    return tuple(
        SessionParticipant(
            name=row["participant_name"],
            normalized_name=row["normalized_participant_name"],
            email=row["participant_email"],
            job_title=row["participant_job_title"],
            department=row["participant_department"],
            resolution_status=row["resolution_status"],
            contact_id=row["contact_id"],
            account_id=row["account_id"],
        )
        for row in rows
    )
