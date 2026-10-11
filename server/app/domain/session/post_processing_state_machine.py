"""세션 후처리 상태 전이 규칙.

세션 상태(draft/running/ended)와는 별개의 상태 기계다.
두 상태 기계를 잇는 불변식은 여기서 함께 검사한다: 후처리는 회의가 끝난 뒤에만 시작할 수 있다.
"""

from __future__ import annotations

from server.app.domain.shared.enums import PostProcessingStatus, SessionStatus

_P = PostProcessingStatus

# 현재 상태 -> 허용된 다음 상태.
# QUEUED -> QUEUED: 같은 세션에 후처리를 다시 요청해도 대기 상태를 유지한다 (멱등).
# PROCESSING -> PROCESSING: 처리 중 worker가 죽어 같은 job이 다시 시작되는 경우.
_ALLOWED_TRANSITIONS: dict[PostProcessingStatus, frozenset[PostProcessingStatus]] = {
    _P.NOT_STARTED: frozenset({_P.QUEUED}),
    _P.QUEUED: frozenset({_P.QUEUED, _P.PROCESSING, _P.FAILED}),
    _P.PROCESSING: frozenset({_P.PROCESSING, _P.COMPLETED, _P.FAILED}),
    # COMPLETED -> FAILED: 후처리는 끝났지만 다음 단계 등록이 실패해 정본을 되돌리는 보상 처리.
    _P.COMPLETED: frozenset({_P.QUEUED, _P.FAILED}),
    _P.FAILED: frozenset({_P.QUEUED}),
}


def ensure_post_processing_transition(
    current: PostProcessingStatus,
    target: PostProcessingStatus,
) -> None:
    """허용되지 않은 후처리 상태 전이면 ValueError를 낸다."""

    if target not in _ALLOWED_TRANSITIONS[current]:
        raise ValueError(
            f"후처리 상태를 {current.value}에서 {target.value}로 바꿀 수 없습니다."
        )


def ensure_session_ended_for_post_processing(session_status: SessionStatus) -> None:
    """회의가 끝나기 전에는 후처리를 요청하거나 시작할 수 없다."""

    if session_status != SessionStatus.ENDED:
        raise ValueError("회의가 끝난 뒤에만 후처리를 요청할 수 있습니다.")
