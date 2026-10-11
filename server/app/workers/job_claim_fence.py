"""worker가 claim한 job에 결과를 쓸 권한이 아직 있는지 확인한다.

lease가 만료돼 다른 worker가 같은 job을 이어받았다면, 늦은 worker의 결과 쓰기는 막아야 한다.
세 종류의 job(세션 후처리, 노트 보정, 리포트 생성)이 같은 규칙을 쓴다.
"""

from __future__ import annotations

from server.app.core.clock import utc_now_iso


class StaleJobClaimError(RuntimeError):
    """처리 중에 다른 worker에게 claim이 넘어가, 이 worker의 쓰기를 막았을 때 발생한다."""


def is_claim_held(repository, job_id: str, worker_id: str | None) -> bool:
    """worker_id가 아직 이 job을 processing 상태로 claim하고 있는지 확인한다. worker_id가 None이면 펜싱하지 않는다."""

    if worker_id is None:
        return True
    current = repository.get_by_id(job_id)
    return (
        current is not None
        and current.status == "processing"
        and current.claimed_by_worker_id == worker_id
    )


def ensure_claim_held(repository, job, worker_id: str | None) -> None:
    """claim을 잃었으면 StaleJobClaimError를 던져 결과 쓰기를 멈춘다."""

    if not is_claim_held(repository, job.id, worker_id):
        raise StaleJobClaimError(f"claim이 다른 worker로 넘어갔습니다: {job.id}")


def write_claimed_job(repository, job, worker_id: str | None):
    """claim을 가진 worker만 job 상태를 완료나 실패로 쓸 수 있다. 권한이 없으면 StaleJobClaimError."""

    if worker_id is None:
        return repository.update(job)
    if not repository.update_if_claimed(job, worker_id=worker_id):
        raise StaleJobClaimError(f"claim이 다른 worker로 넘어가 상태를 쓰지 않았습니다: {job.id}")
    return job


def resolve_processing_job(
    repository,
    *,
    job_id: str,
    expected_worker_id: str | None,
    label: str,
):
    """처리 가능한 job을 확인하고 processing 상태의 job을 돌려준다.

    expected_worker_id가 있으면 그 worker가 claim한 job만 받는다. 없으면(인프로세스 처리) 상태를 processing으로 바꾼다.
    label은 오류 문구에 쓰는 job 이름이다(예: "세션 후처리 job").
    """

    job = repository.get_by_id(job_id)
    if job is None:
        raise ValueError(f"{label}을 찾을 수 없습니다: {job_id}")
    if job.status == "completed":
        return job

    if expected_worker_id is not None:
        if job.status != "processing":
            raise ValueError(f"claim되지 않은 {label}입니다: {job_id}")
        if job.claimed_by_worker_id != expected_worker_id:
            raise ValueError(f"다른 worker가 claim한 {label}입니다: {job_id}")
        return job

    if job.status == "processing":
        return job

    return repository.update(job.mark_processing(started_at=utc_now_iso()))
