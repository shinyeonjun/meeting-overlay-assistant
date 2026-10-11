"""세 종류 job이 같은 상태 전이 규칙을 따르는지 검증한다 (DB 없음)."""

from __future__ import annotations

import pytest

from server.app.domain.models.note_correction_job import NoteCorrectionJob
from server.app.domain.models.report_generation_job import ReportGenerationJob
from server.app.domain.models.session_post_processing_job import SessionPostProcessingJob


def _pending_jobs():
    yield NoteCorrectionJob.create_pending(session_id="s1", source_version=1)
    yield ReportGenerationJob.create_pending(
        session_id="s1", recording_artifact_id=None, recording_path=None
    )
    yield SessionPostProcessingJob.create_pending(session_id="s1", recording_artifact_id=None, recording_path=None)


@pytest.mark.parametrize("job", list(_pending_jobs()), ids=lambda job: type(job).__name__)
def test_pending에서_processing과_failed로만_갈_수_있다(job):
    assert job.mark_processing(claimed_by_worker_id="w1").status == "processing"
    assert job.mark_failed("입력 없음").status == "failed"
    with pytest.raises(ValueError, match="pending에서 completed"):
        job.mark_completed(**_completed_kwargs(job))


@pytest.mark.parametrize("job", list(_pending_jobs()), ids=lambda job: type(job).__name__)
def test_completed_job은_다시_처리할_수_없다(job):
    done = job.mark_processing(claimed_by_worker_id="w1").mark_completed(**_completed_kwargs(job))

    with pytest.raises(ValueError, match="completed에서 processing"):
        done.mark_processing(claimed_by_worker_id="w2")


@pytest.mark.parametrize("job", list(_pending_jobs()), ids=lambda job: type(job).__name__)
def test_만료된_processing_job은_다른_worker가_다시_claim할_수_있다(job):
    claimed = job.mark_processing(claimed_by_worker_id="w1")

    reclaimed = claimed.mark_processing(claimed_by_worker_id="w2")

    assert reclaimed.status == "processing"
    assert reclaimed.attempt_count == 2


def _completed_kwargs(job) -> dict:
    if isinstance(job, ReportGenerationJob):
        return {"transcript_path": None, "markdown_report_id": None, "pdf_report_id": None}
    return {}
