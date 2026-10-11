"""회의 세션의 하위 상태를 값 객체로 묶는다.

MeetingSession은 생명주기(status)와 식별 정보만 직접 갖고,
복구 상태와 후처리 상태는 각각 독립된 값 객체로 둔다. 바꿀 때는 새 값을 만든다(불변).
"""

from __future__ import annotations

from dataclasses import dataclass

from server.app.domain.shared.enums import PostProcessingStatus


@dataclass(frozen=True)
class RecoveryState:
    """비정상 종료 후 복구가 필요한지 나타낸다."""

    required: bool = False
    reason: str | None = None
    detected_at: str | None = None


@dataclass(frozen=True)
class PostProcessingState:
    """회의 종료 후 녹음 재전사와 정본 생성 과정의 상태."""

    status: PostProcessingStatus = PostProcessingStatus.NOT_STARTED
    error_message: str | None = None
    requested_at: str | None = None
    started_at: str | None = None
    completed_at: str | None = None
    canonical_transcript_version: int = 0
    canonical_events_version: int = 0
