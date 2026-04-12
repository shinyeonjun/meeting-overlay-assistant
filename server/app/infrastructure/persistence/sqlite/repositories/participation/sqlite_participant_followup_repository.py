"""SQLite 참여자 후속 작업 저장소 구현."""

from __future__ import annotations

from datetime import datetime, timezone

from server.app.domain.participation import ParticipantFollowup
from server.app.infrastructure.persistence.sqlite.database import Database
from server.app.repositories.contracts.participation import ParticipantFollowupRepository


class SQLiteParticipantFollowupRepository(ParticipantFollowupRepository):
    """SQLite 기반 참여자 후속 작업 저장소."""

    def __init__(self, database: Database) -> None:
        self._database = database

    def upsert_pending(self, followup: ParticipantFollowup) -> ParticipantFollowup:
        with self._database.connect() as connection:
            connection.execute(
                """
                INSERT INTO participant_followups (
                    id,
                    session_id,
                    participant_order,
                    participant_name,
                    resolution_status,
                    followup_status,
                    matched_contact_count,
                    contact_id,
                    account_id,
                    created_at,
                    updated_at,
                    resolved_at,
                    resolved_by_user_id
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(session_id, participant_order) DO UPDATE SET
                    participant_name = excluded.participant_name,
                    resolution_status = excluded.resolution_status,
                    followup_status = 'pending',
                    matched_contact_count = excluded.matched_contact_count,
                    contact_id = excluded.contact_id,
                    account_id = excluded.account_id,
                    updated_at = excluded.updated_at,
                    resolved_at = NULL,
                    resolved_by_user_id = NULL
                """,
                (
                    followup.id,
                    followup.session_id,
                    followup.participant_order,
                    followup.participant_name,
                    followup.resolution_status,
                    followup.followup_status,
                    followup.matched_contact_count,
                    followup.contact_id,
                    followup.account_id,
                    followup.created_at,
                    followup.updated_at,
                    followup.resolved_at,
                    followup.resolved_by_user_id,
                ),
            )
            connection.commit()

        return self._get_by_session_and_order(
            session_id=followup.session_id,
            participant_order=followup.participant_order,
        )

    def mark_resolved(
        self,
        *,
        session_id: str,
        participant_name: str,
        contact_id: str | None = None,
        resolved_by_user_id: str | None = None,
    ) -> None:
        resolved_at = datetime.now(timezone.utc).isoformat()
        with self._database.connect() as connection:
            connection.execute(
                """
                UPDATE participant_followups
                SET
                    followup_status = 'resolved',
                    contact_id = COALESCE(?, contact_id),
                    updated_at = ?,
                    resolved_at = ?,
                    resolved_by_user_id = ?
                WHERE session_id = ? AND participant_name = ? AND followup_status != 'resolved'
                """,
                (
                    contact_id,
                    resolved_at,
                    resolved_at,
                    resolved_by_user_id,
                    session_id,
                    participant_name.strip(),
                ),
            )
            connection.commit()

    def list_by_session(
        self,
        *,
        session_id: str,
        followup_status: str | None = None,
    ) -> list[ParticipantFollowup]:
        query = """
            SELECT *
            FROM participant_followups
            WHERE session_id = ?
        """
        params: list[object] = [session_id]
        if followup_status is not None:
            query += " AND followup_status = ?"
            params.append(followup_status)
        query += " ORDER BY participant_order ASC"

        with self._database.connect() as connection:
            rows = connection.execute(query, tuple(params)).fetchall()
        return [self._to_followup(row) for row in rows]

    def _get_by_session_and_order(
        self,
        *,
        session_id: str,
        participant_order: int,
    ) -> ParticipantFollowup:
        with self._database.connect() as connection:
            row = connection.execute(
                """
                SELECT *
                FROM participant_followups
                WHERE session_id = ? AND participant_order = ?
                """,
                (session_id, participant_order),
            ).fetchone()
        return self._to_followup(row)

    @staticmethod
    def _to_followup(row) -> ParticipantFollowup:
        return ParticipantFollowup(
            id=row["id"],
            session_id=row["session_id"],
            participant_order=row["participant_order"],
            participant_name=row["participant_name"],
            resolution_status=row["resolution_status"],
            followup_status=row["followup_status"],
            matched_contact_count=row["matched_contact_count"],
            contact_id=row["contact_id"],
            account_id=row["account_id"],
            created_at=row["created_at"],
            updated_at=row["updated_at"],
            resolved_at=row["resolved_at"],
            resolved_by_user_id=row["resolved_by_user_id"],
        )
