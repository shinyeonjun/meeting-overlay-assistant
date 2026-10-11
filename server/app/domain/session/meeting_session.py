"""회의 세션 코어 엔티티."""

from __future__ import annotations

from dataclasses import dataclass, field, replace
from uuid import uuid4

from server.app.contexts.participation import (
    SessionParticipant,
    normalize_session_participants,
)
from server.app.domain.session.post_processing_state_machine import (
    ensure_post_processing_transition,
    ensure_session_ended_for_post_processing,
)
from server.app.domain.session.session_state_machine import (
    end_meeting_session,
    start_meeting_session,
    utc_now_iso,
)
from server.app.domain.session.session_states import PostProcessingState, RecoveryState
from server.app.domain.shared.enums import (
    AudioSource,
    PostProcessingStatus,
    SessionMode,
    SessionStatus,
)


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
    recovery: RecoveryState = field(default_factory=RecoveryState)
    post_processing: PostProcessingState = field(default_factory=PostProcessingState)
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

    def ensure_deletable(self) -> None:
        """진행 중인 회의는 먼저 종료해야 삭제할 수 있다."""

        if self.status == SessionStatus.RUNNING:
            raise ValueError("진행 중인 회의는 먼저 종료해야 삭제할 수 있습니다.")
        if self.post_processing_status in (PostProcessingStatus.QUEUED, PostProcessingStatus.PROCESSING):
            raise ValueError("후처리가 진행 중인 회의는 후처리가 끝난 뒤 삭제할 수 있습니다.")

    def ensure_reprocessable(self) -> None:
        """진행 중인 회의는 노트를 다시 만들 수 없다."""

        if self.status == SessionStatus.RUNNING:
            raise ValueError("진행 중인 회의는 노트를 다시 만들 수 없습니다.")

    def mark_recovery_required(self, reason: str) -> "MeetingSession":
        """비정상 종료된 세션을 복구 필요 상태로 표시한다."""

        normalized_reason = reason.strip()
        if not normalized_reason:
            raise ValueError("복구 사유는 비워둘 수 없습니다.")

        ended_session = self if self.status == SessionStatus.ENDED else self.end()
        return replace(
            ended_session,
            recovery=RecoveryState(
                required=True,
                reason=normalized_reason,
                detected_at=utc_now_iso(),
            ),
        )

    def clear_recovery_required(self) -> "MeetingSession":
        """복구 필요 상태를 해제한다."""

        if self.recovery == RecoveryState():
            return self
        return replace(self, recovery=RecoveryState())

    # 기존 호출부가 쓰는 평평한 이름. 값은 하위 값 객체에서 읽는다 (쓰기는 전이 메서드로만).
    @property
    def recovery_required(self) -> bool:
        return self.recovery.required

    @property
    def recovery_reason(self) -> str | None:
        return self.recovery.reason

    @property
    def recovery_detected_at(self) -> str | None:
        return self.recovery.detected_at

    @property
    def post_processing_status(self) -> PostProcessingStatus:
        return self.post_processing.status

    @property
    def post_processing_error_message(self) -> str | None:
        return self.post_processing.error_message

    @property
    def post_processing_requested_at(self) -> str | None:
        return self.post_processing.requested_at

    @property
    def post_processing_started_at(self) -> str | None:
        return self.post_processing.started_at

    @property
    def post_processing_completed_at(self) -> str | None:
        return self.post_processing.completed_at

    @property
    def canonical_transcript_version(self) -> int:
        return self.post_processing.canonical_transcript_version

    @property
    def canonical_events_version(self) -> int:
        return self.post_processing.canonical_events_version

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
        """세션 제목을 변경한다."""

        normalized = title.strip()
        if not normalized:
            raise ValueError("세션 제목은 비어 있을 수 없습니다.")
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

        ensure_session_ended_for_post_processing(self.status)
        ensure_post_processing_transition(
            self.post_processing_status,
            PostProcessingStatus.QUEUED,
        )
        return replace(
            self,
            recovery=RecoveryState(),
            recording_artifact_id=recording_artifact_id or self.recording_artifact_id,
            post_processing=replace(
                self.post_processing,
                status=PostProcessingStatus.QUEUED,
                error_message=None,
                requested_at=utc_now_iso(),
                started_at=None,
                completed_at=None,
            ),
        )
    def mark_post_processing_started(
        self,
        *,
        recording_artifact_id: str | None = None,
    ) -> "MeetingSession":
        """세션 후처리 시작 상태를 기록한다."""

        ensure_session_ended_for_post_processing(self.status)
        ensure_post_processing_transition(
            self.post_processing_status,
            PostProcessingStatus.PROCESSING,
        )
        return replace(
            self,
            recovery=RecoveryState(),
            recording_artifact_id=recording_artifact_id or self.recording_artifact_id,
            post_processing=replace(
                self.post_processing,
                status=PostProcessingStatus.PROCESSING,
                error_message=None,
                started_at=utc_now_iso(),
                completed_at=None,
            ),
        )
    def mark_post_processing_completed(
        self,
        *,
        recording_artifact_id: str | None = None,
    ) -> "MeetingSession":
        """세션 후처리 완료 상태를 기록한다."""

        ensure_post_processing_transition(
            self.post_processing_status,
            PostProcessingStatus.COMPLETED,
        )
        return replace(
            self,
            recovery=RecoveryState(),
            recording_artifact_id=recording_artifact_id or self.recording_artifact_id,
            post_processing=replace(
                self.post_processing,
                status=PostProcessingStatus.COMPLETED,
                error_message=None,
                completed_at=utc_now_iso(),
                canonical_transcript_version=self.post_processing.canonical_transcript_version + 1,
                canonical_events_version=self.post_processing.canonical_events_version + 1,
            ),
        )
    def mark_post_processing_failed(
        self,
        error_message: str,
        *,
        recording_artifact_id: str | None = None,
    ) -> "MeetingSession":
        """세션 후처리 실패 상태를 기록한다."""

        ensure_post_processing_transition(
            self.post_processing_status,
            PostProcessingStatus.FAILED,
        )
        return replace(
            self,
            recovery=RecoveryState(),
            recording_artifact_id=recording_artifact_id or self.recording_artifact_id,
            post_processing=replace(
                self.post_processing,
                status=PostProcessingStatus.FAILED,
                error_message=error_message,
                completed_at=utc_now_iso(),
            ),
        )
