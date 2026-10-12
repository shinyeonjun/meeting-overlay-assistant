"""session 후처리 job의 enqueue, dispatch, lease, claim, 조회 메서드를 제공한다."""

from __future__ import annotations

from server.app.contexts.live_capture import find_session_recording_artifact
from server.app.contexts.reporting import utc_after_seconds_iso, utc_now_iso
from server.app.core.config import settings
from server.app.domain.models.session_post_processing_job import SessionPostProcessingJob


class SessionPostProcessingDispatchMixin:
    """`SessionPostProcessingJobService`가 상속하는 큐 발행과 job 조회 메서드 묶음이다.

    인스턴스 속성(_repository, _session_repository, _job_queue, _artifact_store)과
    process_job은 서비스 클래스가 제공한다.
    """

    def enqueue_for_session(
        self,
        *,
        session_id: str,
        requested_by_user_id: str | None = None,
        dispatch: bool = True,
    ) -> SessionPostProcessingJob:
        """세션 기준 최신 pending job을 재사용하거나 새로 만든다."""

        session = self._session_repository.get_by_id(session_id)
        if session is None:
            raise ValueError(f"존재하지 않는 세션입니다: {session_id}")

        latest_job = self._repository.get_latest_by_session(session_id)
        if latest_job is not None and latest_job.status == "processing":
            return latest_job
        if latest_job is not None and latest_job.status == "pending":
            self._session_repository.save(
                session.queue_post_processing(
                    recording_artifact_id=latest_job.recording_artifact_id,
                )
            )
            if dispatch:
                self.dispatch_job(latest_job.id)
            return latest_job

        recording_artifact = self._resolve_recording_artifact(session_id)
        queued_session = session.queue_post_processing(
            recording_artifact_id=(recording_artifact.artifact_id if recording_artifact is not None else None),
        )
        self._session_repository.save(queued_session)

        job = SessionPostProcessingJob.create_pending(
            session_id=session_id,
            recording_artifact_id=queued_session.recording_artifact_id,
            recording_path=(str(recording_artifact.file_path) if recording_artifact is not None else None),
            requested_by_user_id=requested_by_user_id,
        )
        saved_job = self._repository.save(job)
        if dispatch:
            self.dispatch_job(saved_job.id)
        return saved_job

    def dispatch_job(self, job_id: str) -> bool:
        """대기 중인 job을 큐에 발행한다."""

        if self._job_queue is None:
            return False
        return self._job_queue.publish(job_id)

    @property
    def has_queue(self) -> bool:
        """후처리 job 큐 사용 여부를 반환한다."""

        return self._job_queue is not None

    def wait_for_dispatched_job(self, timeout_seconds: float) -> str | None:
        """큐에서 후처리 job 신호를 기다린다."""

        if self._job_queue is None:
            return None
        return self._job_queue.wait_for_job(timeout_seconds)

    def renew_job_lease(
        self,
        *,
        job_id: str,
        worker_id: str,
        lease_duration_seconds: int,
    ) -> bool:
        """처리 중인 job lease를 연장한다."""

        return self._repository.renew_lease(
            job_id=job_id,
            worker_id=worker_id,
            lease_expires_at=utc_after_seconds_iso(lease_duration_seconds),
        )

    def get_latest_job(self, session_id: str) -> SessionPostProcessingJob | None:
        """세션 기준 최신 후처리 job을 조회한다."""

        return self._repository.get_latest_by_session(session_id)

    def list_pending_jobs(self, limit: int = 10) -> list[SessionPostProcessingJob]:
        """처리 대기 중인 후처리 job 목록을 반환한다."""

        return self._repository.list_pending(limit=limit)

    def claim_available_jobs(
        self,
        *,
        worker_id: str,
        lease_duration_seconds: int,
        limit: int = 10,
    ) -> list[SessionPostProcessingJob]:
        """pending 또는 lease 만료 job을 claim한다."""

        return self._repository.claim_available(
            worker_id=worker_id,
            lease_expires_at=utc_after_seconds_iso(lease_duration_seconds),
            claimed_at=utc_now_iso(),
            limit=limit,
            max_attempts=settings.pipeline_job_max_attempts,
        )

    def process_available_jobs(
        self,
        *,
        worker_id: str,
        lease_duration_seconds: int,
        limit: int = 10,
    ) -> list[SessionPostProcessingJob]:
        """worker가 claim 가능한 job을 가져와 순서대로 처리한다."""

        claimed_jobs = self.claim_available_jobs(
            worker_id=worker_id,
            lease_duration_seconds=lease_duration_seconds,
            limit=limit,
        )
        return [self.process_job(job.id, expected_worker_id=worker_id) for job in claimed_jobs]

    def process_latest_pending_for_session(
        self,
        session_id: str,
    ) -> SessionPostProcessingJob | None:
        """세션 기준 최신 pending job 하나를 처리한다."""

        latest_job = self._repository.get_latest_by_session(session_id)
        if latest_job is None or latest_job.status != "pending":
            return latest_job
        return self.process_job(latest_job.id)

    def _resolve_recording_artifact(self, session_id: str):
        return find_session_recording_artifact(
            session_id,
            artifact_store=self._artifact_store,
        )
