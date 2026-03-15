"""참여자 contact/account 해석 서비스."""

from __future__ import annotations

from server.app.domain.context import ContactContext
from server.app.domain.participation import (
    SessionParticipant,
    SessionParticipantCandidate,
    SessionParticipantCandidateMatch,
    normalize_participant_name,
    normalize_participant_names,
)
from server.app.domain.session import MeetingSession


class ParticipantResolutionService:
    """세션 참여자를 contact/account에 연결하는 규칙을 담당한다."""

    def __init__(
        self,
        meeting_context_repository=None,
    ) -> None:
        self._meeting_context_repository = meeting_context_repository

    def resolve_initial_participant_links(
        self,
        *,
        workspace_id: str,
        account_id: str | None,
        contact_id: str | None,
        participants: list[str] | tuple[str, ...] | None,
    ) -> tuple[SessionParticipant, ...]:
        normalized_names = normalize_participant_names(participants)
        if not normalized_names:
            return ()

        linked_by_name: dict[str, SessionParticipant] = {}
        if self._meeting_context_repository is not None:
            grouped_candidates = self._list_contacts_grouped_by_name(
                workspace_id=workspace_id,
                names=normalized_names,
                account_id=account_id,
            )
            for name in normalized_names:
                matches = grouped_candidates.get(name, [])
                if len(matches) == 1:
                    matched = matches[0]
                    linked_by_name[name] = SessionParticipant(
                        name=name,
                        normalized_name=normalize_participant_name(name),
                        contact_id=matched.id,
                        account_id=matched.account_id or account_id,
                        email=matched.email,
                        job_title=matched.job_title,
                        department=matched.department,
                        resolution_status="linked",
                    )

            if contact_id is not None:
                explicit_contact = self._meeting_context_repository.get_contact(
                    contact_id=contact_id,
                    workspace_id=workspace_id,
                )
                if explicit_contact is not None:
                    explicit_name = explicit_contact.name.strip()
                    if explicit_name in normalized_names:
                        linked_by_name[explicit_name] = SessionParticipant(
                            name=explicit_name,
                            normalized_name=normalize_participant_name(explicit_name),
                            contact_id=explicit_contact.id,
                            account_id=explicit_contact.account_id or account_id,
                            email=explicit_contact.email,
                            job_title=explicit_contact.job_title,
                            department=explicit_contact.department,
                            resolution_status="linked",
                        )

        grouped_candidates = self._list_contacts_grouped_by_name(
            workspace_id=workspace_id,
            names=normalized_names,
            account_id=account_id,
        )
        resolved: list[SessionParticipant] = []
        for name in normalized_names:
            if name in linked_by_name:
                resolved.append(linked_by_name[name])
                continue
            matched_contact_count = len(grouped_candidates.get(name, []))
            resolved.append(
                SessionParticipant(
                    name=name,
                    normalized_name=normalize_participant_name(name),
                    account_id=account_id,
                    resolution_status=(
                        "ambiguous" if matched_contact_count > 1 else "unmatched"
                    ),
                )
            )
        return tuple(resolved)

    def build_participant_candidates(
        self,
        *,
        session: MeetingSession,
        workspace_id: str,
    ) -> tuple[SessionParticipantCandidate, ...]:
        """contact로 승격 가능한 참여자 후보를 계산한다."""

        candidates_by_name = self._build_participant_candidates_by_name(
            session=session,
            workspace_id=workspace_id,
        )
        if not candidates_by_name:
            return ()

        return tuple(
            candidates_by_name[item.name]
            for item in session.participant_links
            if item.contact_id is None and item.name in candidates_by_name
        )

    def get_participant_candidate(
        self,
        *,
        session: MeetingSession,
        workspace_id: str,
        participant_name: str,
    ) -> SessionParticipantCandidate | None:
        """특정 참여자 후보를 찾는다."""

        normalized_name = participant_name.strip()
        if not normalized_name:
            return None

        return self._build_participant_candidates_by_name(
            session=session,
            workspace_id=workspace_id,
        ).get(normalized_name)

    def _build_participant_candidates_by_name(
        self,
        *,
        session: MeetingSession,
        workspace_id: str,
    ) -> dict[str, SessionParticipantCandidate]:
        unresolved_names = tuple(
            item.name
            for item in session.participant_links
            if item.contact_id is None
        )
        if not unresolved_names:
            return {}

        grouped_candidates = self._list_contacts_grouped_by_name(
            workspace_id=workspace_id,
            names=unresolved_names,
            account_id=session.account_id,
        )
        candidates_by_name: dict[str, SessionParticipantCandidate] = {}
        for item in session.participant_links:
            if item.contact_id is not None or item.name in candidates_by_name:
                continue

            matched_contacts = tuple(
                SessionParticipantCandidateMatch(
                    contact_id=candidate.id,
                    account_id=candidate.account_id,
                    name=candidate.name,
                    email=candidate.email,
                    job_title=candidate.job_title,
                    department=candidate.department,
                )
                for candidate in grouped_candidates.get(item.name, [])
            )
            matched_contact_count = len(matched_contacts)
            candidates_by_name[item.name] = SessionParticipantCandidate(
                name=item.name,
                account_id=item.account_id or session.account_id,
                resolution_status=(
                    "ambiguous"
                    if matched_contact_count > 1
                    else "unmatched"
                ),
                matched_contact_count=matched_contact_count,
                matched_contacts=matched_contacts,
            )
        return candidates_by_name

    def _list_contacts_grouped_by_name(
        self,
        *,
        workspace_id: str,
        names: list[str] | tuple[str, ...],
        account_id: str | None,
    ) -> dict[str, list[ContactContext]]:
        if self._meeting_context_repository is None or not names:
            return {}

        grouped_candidates: dict[str, list[ContactContext]] = {}
        candidate_contacts = self._meeting_context_repository.list_contacts_by_names(
            workspace_id=workspace_id,
            names=names,
            account_id=account_id,
        )
        for candidate in candidate_contacts:
            grouped_candidates.setdefault(candidate.name.strip(), []).append(candidate)
        return grouped_candidates
