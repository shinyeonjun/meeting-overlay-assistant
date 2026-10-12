"""재시도 상한에 도달한 후처리 job이 세션 상태를 failed로 확정하는지 검증한다."""

from __future__ import annotations

from types import SimpleNamespace

from server.app.domain.shared.enums import AudioSource, SessionMode
from server.app.infrastructure.persistence.postgresql.repositories.session import (
    PostgreSQLSessionRepository,
)
from server.app.contexts.post_processing import (
    PostMeetingPipelineRecoveryService,
)
from server.app.contexts.meeting import SessionService


class _PostProcessingJobService:
    def __init__(self, latest_job) -> None:
        self._latest_job = latest_job
        self.enqueued: list[str] = []

    def get_latest_job(self, session_id: str):
        return self._latest_job

    def enqueue_for_session(self, *, session_id: str, requested_by_user_id, dispatch: bool):
        self.enqueued.append(session_id)

    def dispatch_job(self, job_id: str) -> bool:
        return True


class _EmptyNoteCorrectionService:
    def get_latest_job(self, session_id: str):
        return None

    def enqueue_for_session(self, **kwargs):
        raise AssertionError("후처리 단계에서는 노트 보정을 건드리지 않는다.")


class _ProcessingStatusService:
    def build_final_status(self, *, session):
        return SimpleNamespace(pipeline_stage="post_processing")


def _build_session_in_post_processing(isolated_database):
    session_repository = PostgreSQLSessionRepository(isolated_database)
    session_service = SessionService(session_repository)
    session = session_service.create_session_draft(
        title="상한 도달 테스트",
        mode=SessionMode.MEETING,
        source=AudioSource.SYSTEM_AUDIO,
    )
    session = session_service.start_session(session.id)
    session = session_service.end_session(session.id)
    session = session_repository.save(
        session.queue_post_processing().mark_post_processing_started(recording_artifact_id=None)
    )
    return session_repository, session


def test_재시도_상한에_도달한_후처리_job이면_세션도_failed로_확정한다(isolated_database):
    session_repository, session = _build_session_in_post_processing(isolated_database)
    exhausted_job = SimpleNamespace(
        id="post-job-exhausted",
        status="failed",
        attempt_count=3,
        error_message="lease 만료가 최대 시도 횟수만큼 반복되어 중단했습니다.",
    )
    post_processing = _PostProcessingJobService(exhausted_job)
    recovery = PostMeetingPipelineRecoveryService(
        session_repository=session_repository,
        session_post_processing_job_service=post_processing,
        note_correction_job_service=_EmptyNoteCorrectionService(),
        report_generation_job_service=_ProcessingStatusService(),
        max_attempts=3,
    )

    summary = recovery.recover(limit=10)
    refreshed = session_repository.get_by_id(session.id)

    assert summary.requeued_post_processing_jobs == 0
    assert post_processing.enqueued == []
    assert refreshed is not None
    assert refreshed.post_processing_status == "failed"
    assert "최대 시도 횟수" in (refreshed.post_processing_error_message or "")


def test_시도_횟수가_남은_실패_job은_세션을_failed로_바꾸지_않고_재큐잉한다(isolated_database):
    session_repository, session = _build_session_in_post_processing(isolated_database)
    retryable_job = SimpleNamespace(
        id="post-job-retry",
        status="failed",
        attempt_count=1,
        error_message="일시적 오류",
    )
    post_processing = _PostProcessingJobService(retryable_job)
    recovery = PostMeetingPipelineRecoveryService(
        session_repository=session_repository,
        session_post_processing_job_service=post_processing,
        note_correction_job_service=_EmptyNoteCorrectionService(),
        report_generation_job_service=_ProcessingStatusService(),
        max_attempts=3,
    )

    summary = recovery.recover(limit=10)
    refreshed = session_repository.get_by_id(session.id)

    assert summary.requeued_post_processing_jobs == 1
    assert post_processing.enqueued == [session.id]
    assert refreshed is not None
    assert refreshed.post_processing_status == "processing"
