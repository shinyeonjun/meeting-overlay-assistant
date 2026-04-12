"""참여자 후속 작업 서비스."""

from __future__ import annotations

from server.app.domain.participation import ParticipantFollowup
from server.app.domain.session import MeetingSession
from server.app.repositories.contracts.participation import ParticipantFollowupRepository
from server.app.services.participation.participant_resolution_service import (
    ParticipantResolutionService,
)


class ParticipantFollowupService:
    """미해결 참여자를 후속 작업으로 저장하고 갱신한다."""

    def __init__(
        self,
        *,
        participant_followup_repository: ParticipantFollowupRepository,
        participant_resolution_service: ParticipantResolutionService,
    ) -> None:
        self._participant_followup_repository = participant_followup_repository
        self._participant_resolution_service = participant_resolution_service

    def sync_followups_for_session(
        self,
        *,
        session: MeetingSession,
        workspace_id: str,
        resolved_by_user_id: str | None = None,
        create_missing: bool = True,
    ) -> tuple[ParticipantFollowup, ...]:
        """세션의 현재 참여자 해석 상태를 후속 작업 정본에 반영한다."""

        pending_by_name = {
            candidate.name: candidate
            for candidate in self._participant_resolution_service.build_participant_candidates(
                session=session,
                workspace_id=workspace_id,
            )
        }

        persisted: list[ParticipantFollowup] = []
        for participant_order, participant in enumerate(session.participant_links):
            candidate = pending_by_name.get(participant.name)
            if candidate is None:
                if participant.contact_id is not None:
                    self._participant_followup_repository.mark_resolved(
                        session_id=session.id,
                        participant_name=participant.name,
                        contact_id=participant.contact_id,
                        resolved_by_user_id=resolved_by_user_id,
                    )
                continue
            if not create_missing:
                continue

            persisted.append(
                self._participant_followup_repository.upsert_pending(
                    ParticipantFollowup.create_pending(
                        session_id=session.id,
                        participant_order=participant_order,
                        participant_name=participant.name,
                        resolution_status=candidate.resolution_status,
                        matched_contact_count=candidate.matched_contact_count,
                        contact_id=participant.contact_id,
                        account_id=candidate.account_id or participant.account_id,
                    )
                )
            )

        return tuple(persisted)

    def list_followups(
        self,
        *,
        session_id: str,
        followup_status: str | None = None,
    ) -> tuple[ParticipantFollowup, ...]:
        """세션별 참여자 후속 작업을 조회한다."""

        return tuple(
            self._participant_followup_repository.list_by_session(
                session_id=session_id,
                followup_status=followup_status,
            )
        )
