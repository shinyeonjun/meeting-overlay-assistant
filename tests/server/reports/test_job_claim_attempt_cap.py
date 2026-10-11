"""lease가 계속 만료되는 poison job이 최대 시도 횟수 뒤에는 claim되지 않는지 검증한다."""

from __future__ import annotations

from server.app.domain.models.report_generation_job import ReportGenerationJob
from server.app.domain.shared.enums import AudioSource, SessionMode
from server.app.infrastructure.persistence.postgresql.repositories.postgresql_report_generation_job_repository import (
    PostgreSQLReportGenerationJobRepository,
)
from server.app.infrastructure.persistence.postgresql.repositories.session import (
    PostgreSQLSessionRepository,
)
from server.app.contexts.meeting import SessionService

# 이미 만료된 lease와 현재 시각을 흉내낸다. 만료 비교는 문자열 대소 비교다.
EXPIRED_LEASE = "2000-01-01T00:00:00+00:00"
NOW = "2026-01-01T00:00:00+00:00"


def test_lease가_반복_만료된_job은_최대_시도_후_claim되지_않고_실패로_확정된다(isolated_database):
    session_service = SessionService(PostgreSQLSessionRepository(isolated_database))
    session = session_service.create_session_draft(
        title="attempt cap 테스트",
        mode=SessionMode.MEETING,
        source=AudioSource.SYSTEM_AUDIO,
    )
    repository = PostgreSQLReportGenerationJobRepository(isolated_database)
    job = repository.save(
        ReportGenerationJob.create_pending(
            session_id=session.id,
            recording_artifact_id=None,
            recording_path=None,
            requested_by_user_id=None,
        )
    )

    max_attempts = 3
    for attempt in range(1, max_attempts + 1):
        claimed = repository.claim_available(
            worker_id=f"worker-{attempt}",
            lease_expires_at=EXPIRED_LEASE,
            claimed_at=NOW,
            limit=5,
            max_attempts=max_attempts,
        )
        # worker가 처리 도중 죽어 lease가 만료된 상황을 매번 만든다.
        assert [item.id for item in claimed] == [job.id]
        assert claimed[0].attempt_count == attempt

    exhausted = repository.claim_available(
        worker_id="worker-4",
        lease_expires_at=EXPIRED_LEASE,
        claimed_at=NOW,
        limit=5,
        max_attempts=max_attempts,
    )

    refreshed = repository.get_by_id(job.id)
    assert exhausted == []
    assert refreshed is not None
    assert refreshed.status == "failed"
    assert refreshed.claimed_by_worker_id is None
    assert "최대 시도 횟수" in (refreshed.error_message or "")


def test_시도_횟수가_남은_만료_job은_그대로_재claim된다(isolated_database):
    session_service = SessionService(PostgreSQLSessionRepository(isolated_database))
    session = session_service.create_session_draft(
        title="재claim 테스트",
        mode=SessionMode.MEETING,
        source=AudioSource.SYSTEM_AUDIO,
    )
    repository = PostgreSQLReportGenerationJobRepository(isolated_database)
    job = repository.save(
        ReportGenerationJob.create_pending(
            session_id=session.id,
            recording_artifact_id=None,
            recording_path=None,
            requested_by_user_id=None,
        )
    )

    first = repository.claim_available(
        worker_id="worker-1",
        lease_expires_at=EXPIRED_LEASE,
        claimed_at=NOW,
        limit=5,
        max_attempts=3,
    )
    second = repository.claim_available(
        worker_id="worker-2",
        lease_expires_at=EXPIRED_LEASE,
        claimed_at=NOW,
        limit=5,
        max_attempts=3,
    )

    assert [item.id for item in first] == [job.id]
    assert [item.id for item in second] == [job.id]
    assert second[0].attempt_count == 2
