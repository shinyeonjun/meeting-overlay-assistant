"""PostgreSQL 참여자 후속 작업 저장소 구현."""

from __future__ import annotations

from server.app.domain.participation import ParticipantFollowup
from server.app.infrastructure.persistence.postgresql.database import PostgreSQLDatabase
from server.app.repositories.contracts.participation import ParticipantFollowupRepository


class PostgreSQLParticipantFollowupRepository(ParticipantFollowupRepository):
    """PostgreSQL 기반 참여자 후속 작업 저장소."""

    def __init__(self, database: PostgreSQLDatabase) -> None:
        self._database = database

    def upsert_pending(self, followup: ParticipantFollowup) -> ParticipantFollowup:
        with self._database.transaction() as connection:
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
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (session_id, participant_order) DO UPDATE SET
                    participant_name = EXCLUDED.participant_name,
                    resolution_status = EXCLUDED.resolution_status,
                    followup_status = 'pending',
                    matched_contact_count = EXCLUDED.matched_contact_count,
                    contact_id = EXCLUDED.contact_id,
                    account_id = EXCLUDED.account_id,
                    updated_at = EXCLUDED.updated_at,
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
            row = connection.execute(
                """
                SELECT *
                FROM participant_followups
                WHERE session_id = %s AND participant_order = %s
                """,
                (followup.session_id, followup.participant_order),
            ).fetchone()
        return self._to_followup(row)

    def mark_resolved(
        self,
        *,
        session_id: str,
        participant_name: str,
        contact_id: str | None = None,
        resolved_by_user_id: str | None = None,
    ) -> None:
        from datetime import datetime, timezone

        resolved_at = datetime.now(timezone.utc).isoformat()
        with self._database.transaction() as connection:
            connection.execute(
                """
                UPDATE participant_followups
                SET
                    followup_status = 'resolved',
                    contact_id = COALESCE(%s, contact_id),
                    updated_at = %s,
                    resolved_at = %s,
                    resolved_by_user_id = %s
                WHERE session_id = %s
                  AND participant_name = %s
                  AND followup_status != 'resolved'
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

    def list_by_session(
        self,
        *,
        session_id: str,
        followup_status: str | None = None,
    ) -> list[ParticipantFollowup]:
        query = """
            SELECT *
            FROM participant_followups
            WHERE session_id = %s
        """
        params: list[object] = [session_id]
        if followup_status is not None:
            query += " AND followup_status = %s"
            params.append(followup_status)
        query += " ORDER BY participant_order ASC"

        with self._database.transaction() as connection:
            rows = connection.execute(query, tuple(params)).fetchall()
        return [self._to_followup(row) for row in rows]

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
