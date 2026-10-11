"""claim 펜싱 공용 helper: claim을 잃은 worker는 job 상태를 쓰지 못한다."""

from __future__ import annotations

from dataclasses import dataclass, replace

import pytest

from server.app.workers.job_claim_fence import (
    StaleJobClaimError,
    ensure_claim_held,
    is_claim_held,
    write_claimed_job,
)


@dataclass(frozen=True)
class _Job:
    id: str
    status: str = "processing"
    claimed_by_worker_id: str | None = "worker-a"


class _Repo:
    def __init__(self, job: _Job) -> None:
        self.job = job
        self.writes: list[_Job] = []

    def get_by_id(self, job_id: str):
        return self.job if self.job.id == job_id else None

    def update_if_claimed(self, job: _Job, *, worker_id: str) -> bool:
        if self.job.status == "processing" and self.job.claimed_by_worker_id == worker_id:
            self.job = job
            self.writes.append(job)
            return True
        return False

    def update(self, job: _Job):
        self.job = job
        self.writes.append(job)
        return job


def test_claim을_가진_worker만_완료를_쓸_수_있다():
    repo = _Repo(_Job(id="job-1"))

    written = write_claimed_job(repo, replace(repo.job, status="completed"), "worker-a")

    assert written.status == "completed"
    assert repo.job.status == "completed"


def test_lease가_넘어간_뒤의_늦은_완료는_거부되고_상태를_바꾸지_않는다():
    repo = _Repo(_Job(id="job-1", claimed_by_worker_id="worker-b"))

    with pytest.raises(StaleJobClaimError):
        write_claimed_job(repo, replace(repo.job, status="completed"), "worker-a")

    assert repo.job.status == "processing"
    assert repo.job.claimed_by_worker_id == "worker-b"
    assert repo.writes == []


def test_worker_id가_없으면_펜싱하지_않는다():
    repo = _Repo(_Job(id="job-1", claimed_by_worker_id=None))

    assert is_claim_held(repo, "job-1", None)
    ensure_claim_held(repo, repo.job, None)
    assert write_claimed_job(repo, replace(repo.job, status="failed"), None).status == "failed"


def test_claim_확인은_다른_job이나_없는_job에_대해_거짓이다():
    repo = _Repo(_Job(id="job-1"))

    assert not is_claim_held(repo, "job-missing", "worker-a")
    assert is_claim_held(repo, "job-1", "worker-a")
    assert not is_claim_held(repo, "job-1", "worker-b")
