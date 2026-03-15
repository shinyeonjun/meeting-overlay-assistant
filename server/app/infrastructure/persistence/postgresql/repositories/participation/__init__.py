"""PostgreSQL 참여자 저장소 모음."""

from server.app.infrastructure.persistence.postgresql.repositories.participation.postgresql_participant_followup_repository import (
    PostgreSQLParticipantFollowupRepository,
)

__all__ = ["PostgreSQLParticipantFollowupRepository"]
