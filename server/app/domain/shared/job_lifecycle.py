"""비동기 job(후처리, 노트 보정, 리포트 생성)의 공통 상태 전이 규칙.

세 종류 job은 같은 상태 기계를 쓴다. 재시도는 기존 job을 되살리지 않고 새 job을 만든다.
그래서 completed와 failed는 종착 상태다.
"""

from __future__ import annotations

from enum import Enum


class JobStatus(str, Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


_P = JobStatus

_ALLOWED_TRANSITIONS: dict[JobStatus, frozenset[JobStatus]] = {
    # PROCESSING -> PROCESSING: lease가 만료된 job을 다른 worker가 다시 claim하는 경우.
    _P.PENDING: frozenset({_P.PROCESSING, _P.FAILED}),
    _P.PROCESSING: frozenset({_P.PROCESSING, _P.COMPLETED, _P.FAILED}),
    _P.COMPLETED: frozenset(),
    _P.FAILED: frozenset(),
}


def ensure_job_transition(job_name: str, current: str, target: JobStatus) -> None:
    """허용되지 않은 job 상태 전이면 ValueError를 낸다."""

    try:
        current_status = JobStatus(current)
    except ValueError as exc:
        raise ValueError(f"알 수 없는 {job_name} 상태입니다: {current}") from exc

    if target not in _ALLOWED_TRANSITIONS[current_status]:
        raise ValueError(
            f"{job_name} 상태를 {current_status.value}에서 {target.value}로 바꿀 수 없습니다."
        )
