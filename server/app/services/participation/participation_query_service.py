"""참여자 조회 전용 서비스."""

from __future__ import annotations

from server.app.domain.participation import (
    ParticipantFollowup,
    SessionParticipationSummary,
    SessionParticipationView,
)
from server.app.domain.session import MeetingSession
from server.app.services.participation.participant_followup_service import (
    ParticipantFollowupService,
)
from server.app.services.participation.participant_resolution_service import (
    ParticipantResolutionService,
)


class ParticipationQueryService:
    """세션 참여자 상세와 후속 작업 요약을 조립한다."""

    def __init__(
        self,
        *,
        participant_resolution_service: ParticipantResolutionService,
        participant_followup_service: ParticipantFollowupService,
    ) -> None:
        self._participant_resolution_service = participant_resolution_service
        self._participant_followup_service = participant_followup_service

    def build_session_participation(
        self,
        *,
        session: MeetingSession,
        workspace_id: str,
    ) -> SessionParticipationView:
        """세션 참여자 상세 조회 모델을 만든다."""

        participant_candidates = self._participant_resolution_service.build_participant_candidates(
            session=session,
            workspace_id=workspace_id,
        )
        followups = self._participant_followup_service.list_followups(session_id=session.id)
        summary = self._build_summary(
            participants=session.participant_links,
            followups=followups,
        )
        return SessionParticipationView(
            session_id=session.id,
            participants=session.participant_links,
            participant_candidates=participant_candidates,
            summary=summary,
        )

    @staticmethod
    def _build_summary(
        *,
        participants,
        followups: tuple[ParticipantFollowup, ...],
    ) -> SessionParticipationSummary:
        linked_count = sum(1 for item in participants if item.contact_id is not None)
        ambiguous_count = sum(1 for item in participants if item.resolution_status == "ambiguous")
        unmatched_count = sum(1 for item in participants if item.resolution_status == "unmatched")
        pending_followup_count = sum(1 for item in followups if item.followup_status == "pending")
        resolved_followup_count = sum(1 for item in followups if item.followup_status == "resolved")
        return SessionParticipationSummary(
            total_count=len(participants),
            linked_count=linked_count,
            unmatched_count=unmatched_count,
            ambiguous_count=ambiguous_count,
            unresolved_count=ambiguous_count + unmatched_count,
            pending_followup_count=pending_followup_count,
            resolved_followup_count=resolved_followup_count,
        )
