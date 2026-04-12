"""회의 세션 코어 엔티티."""

from __future__ import annotations

from dataclasses import dataclass, replace
from uuid import uuid4

from server.app.domain.participation import (
    SessionParticipant,
    normalize_session_participants,
)
from server.app.domain.session.session_state_machine import (
    end_meeting_session,
    start_meeting_session,
    utc_now_iso,
)
from server.app.domain.shared.enums import AudioSource, SessionMode, SessionStatus


@dataclass(frozen=True)
class MeetingSession:
    """회의 자체를 표현하는 세션 코어 엔티티."""

    id: str
    title: str
    mode: SessionMode
    primary_input_source: str
    status: SessionStatus
    started_at: str
    created_by_user_id: str | None = None
    account_id: str | None = None
    contact_id: str | None = None
    context_thread_id: str | None = None
    ended_at: str | None = None
    recording_artifact_id: str | None = None
    post_processing_status: str = "not_started"
    post_processing_error_message: str | None = None
    post_processing_requested_at: str | None = None
    post_processing_started_at: str | None = None
    post_processing_completed_at: str | None = None
    canonical_transcript_version: int = 0
    canonical_events_version: int = 0
    actual_active_sources: tuple[str, ...] = ()
    participant_links: tuple[SessionParticipant, ...] = ()

    @classmethod
    def create_draft(
        cls,
        title: str,
        mode: SessionMode,
        source: AudioSource,
        *,
        created_by_user_id: str | None = None,
        account_id: str | None = None,
        contact_id: str | None = None,
        context_thread_id: str | None = None,
        participants: list[str] | tuple[str, ...] | None = None,
        participant_links: list[SessionParticipant] | tuple[SessionParticipant, ...] | None = None,
    ) -> "MeetingSession":
        """초기 draft 세션을 만든다."""

        created_at = utc_now_iso()
        normalized_participants = normalize_session_participants(
            participants=participants,
            participant_links=participant_links,
            default_account_id=account_id,
        )
        return cls(
            id=f"session-{uuid4().hex}",
            title=title,
            mode=mode,
            primary_input_source=source.value,
            status=SessionStatus.DRAFT,
            started_at=created_at,
            created_by_user_id=created_by_user_id,
            account_id=account_id,
            contact_id=contact_id,
            context_thread_id=context_thread_id,
            actual_active_sources=(),
            participant_links=normalized_participants,
        )

    @classmethod
    def start(
        cls,
        title: str,
        mode: SessionMode,
        source: AudioSource,
        *,
        created_by_user_id: str | None = None,
        account_id: str | None = None,
        contact_id: str | None = None,
        context_thread_id: str | None = None,
        participants: list[str] | tuple[str, ...] | None = None,
        participant_links: list[SessionParticipant] | tuple[SessionParticipant, ...] | None = None,
    ) -> "MeetingSession":
        """즉시 running 상태로 시작하는 세션을 만든다."""

        return cls.create_draft(
            title=title,
            mode=mode,
            source=source,
            created_by_user_id=created_by_user_id,
            account_id=account_id,
            contact_id=contact_id,
            context_thread_id=context_thread_id,
            participants=participants,
            participant_links=participant_links,
        ).start_running()

    def start_running(self) -> "MeetingSession":
        """기존 draft 세션을 running 상태로 전이한다."""

        return start_meeting_session(self)

    def end(self) -> "MeetingSession":
        """세션을 ended 상태로 전이한다."""

        return end_meeting_session(self)

    @property
    def participants(self) -> tuple[str, ...]:
        """세션 참여자 이름 목록을 반환한다."""

        return tuple(item.name for item in self.participant_links)

    def mark_active_source(self, input_source: str) -> "MeetingSession":
        """실제로 사용된 입력 소스를 기록한다."""

        normalized = input_source.strip()
        if not normalized or normalized in self.actual_active_sources:
            return self
        return replace(self, actual_active_sources=(*self.actual_active_sources, normalized))

    def rename_title(self, title: str) -> "MeetingSession":
        """?몄뀡 ?쒕ぉ??蹂寃쏀븳??"""

        normalized = title.strip()
        if not normalized:
            raise ValueError("?몄뀡 ?쒕ぉ??鍮꾩뼱 ?덉쓣 ???놁뒿?덈떎.")
        if normalized == self.title:
            return self
        return replace(self, title=normalized)

    def link_participant_contact(
        self,
        participant_name: str,
        *,
        contact_id: str,
        account_id: str | None = None,
        email: str | None = None,
        job_title: str | None = None,
        department: str | None = None,
    ) -> "MeetingSession":
        """참여자를 contact에 연결한다."""

        normalized_name = participant_name.strip()
        if not normalized_name:
            raise ValueError("참여자 이름이 비어 있습니다.")

        matched = False
        updated_links: list[SessionParticipant] = []
        for item in self.participant_links:
            if item.name == normalized_name:
                matched = True
                updated_links.append(
                    SessionParticipant(
                        name=item.name,
                        normalized_name=item.normalized_name,
                        contact_id=contact_id,
                        account_id=account_id or item.account_id or self.account_id,
                        email=email or item.email,
                        job_title=job_title or item.job_title,
                        department=department or item.department,
                        resolution_status="linked",
                    )
                )
                continue
            updated_links.append(item)

        if not matched:
            raise ValueError(f"참여자를 찾지 못했습니다: {participant_name}")

        return replace(self, participant_links=tuple(updated_links))

    def queue_post_processing(
        self,
        *,
        recording_artifact_id: str | None = None,
    ) -> "MeetingSession":
        """세션 후처리 대기 상태를 기록한다."""

        return replace(
            self,
            recording_artifact_id=recording_artifact_id or self.recording_artifact_id,
            post_processing_status="queued",
            post_processing_error_message=None,
            post_processing_requested_at=utc_now_iso(),
            post_processing_started_at=None,
            post_processing_completed_at=None,
        )

    def mark_post_processing_started(
        self,
        *,
        recording_artifact_id: str | None = None,
    ) -> "MeetingSession":
        """세션 후처리 시작 상태를 기록한다."""

        return replace(
            self,
            recording_artifact_id=recording_artifact_id or self.recording_artifact_id,
            post_processing_status="processing",
            post_processing_error_message=None,
            post_processing_started_at=utc_now_iso(),
            post_processing_completed_at=None,
        )

    def mark_post_processing_completed(
        self,
        *,
        recording_artifact_id: str | None = None,
    ) -> "MeetingSession":
        """세션 후처리 완료 상태를 기록한다."""

        return replace(
            self,
            recording_artifact_id=recording_artifact_id or self.recording_artifact_id,
            post_processing_status="completed",
            post_processing_error_message=None,
            post_processing_completed_at=utc_now_iso(),
            canonical_transcript_version=self.canonical_transcript_version + 1,
            canonical_events_version=self.canonical_events_version + 1,
        )

    def mark_post_processing_failed(
        self,
        error_message: str,
        *,
        recording_artifact_id: str | None = None,
    ) -> "MeetingSession":
        """세션 후처리 실패 상태를 기록한다."""

        return replace(
            self,
            recording_artifact_id=recording_artifact_id or self.recording_artifact_id,
            post_processing_status="failed",
            post_processing_error_message=error_message,
            post_processing_completed_at=utc_now_iso(),
        )
