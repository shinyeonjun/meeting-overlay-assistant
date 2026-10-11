"""세션 참여자 snapshot 모델."""

from __future__ import annotations

from dataclasses import dataclass


def normalize_participant_name(value: str) -> str:
    """참여자 이름을 검색/매핑용 문자열로 정규화한다."""

    return " ".join(value.strip().split()).casefold()


@dataclass(frozen=True)
class SessionParticipant:
    """세션 참여자와 contact 연결 상태."""

    name: str
    normalized_name: str
    contact_id: str | None = None
    account_id: str | None = None
    email: str | None = None
    job_title: str | None = None
    department: str | None = None
    resolution_status: str = "unmatched"


def normalize_participant_names(
    participants: list[str] | tuple[str, ...] | None,
) -> tuple[str, ...]:
    """참여자 이름 목록을 중복 없이 정규화한다."""

    if not participants:
        return ()

    normalized: list[str] = []
    seen: set[str] = set()
    for raw_value in participants:
        value = raw_value.strip()
        if not value or value in seen:
            continue
        normalized.append(value)
        seen.add(value)
    return tuple(normalized)


def normalize_session_participants(
    *,
    participants: list[str] | tuple[str, ...] | None,
    participant_links: list[SessionParticipant] | tuple[SessionParticipant, ...] | None,
    default_account_id: str | None = None,
) -> tuple[SessionParticipant, ...]:
    """참여자 이름 순서를 기준으로 세션 참여자 snapshot을 정규화한다."""

    participant_names = normalize_participant_names(participants)
    if not participant_names and participant_links:
        participant_names = normalize_participant_names(
            [item.name for item in participant_links],
        )
    if not participant_names:
        return ()

    linked_by_name: dict[str, SessionParticipant] = {}
    if participant_links:
        for item in participant_links:
            normalized_name = item.name.strip()
            if not normalized_name or normalized_name in linked_by_name:
                continue
            linked_by_name[normalized_name] = SessionParticipant(
                name=normalized_name,
                normalized_name=normalize_participant_name(normalized_name),
                contact_id=item.contact_id,
                account_id=item.account_id or default_account_id,
                email=item.email,
                job_title=item.job_title,
                department=item.department,
                resolution_status=item.resolution_status,
            )

    normalized: list[SessionParticipant] = []
    for name in participant_names:
        normalized.append(
            linked_by_name.get(
                name,
                SessionParticipant(
                    name=name,
                    normalized_name=normalize_participant_name(name),
                    account_id=default_account_id,
                ),
            )
        )
    return tuple(normalized)
