"""시각 컬럼이 TIMESTAMPTZ여도 애플리케이션에는 UTC ISO 문자열로 전달되는지 검증한다."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from server.app.domain.models.report_generation_job import ReportGenerationJob
from server.app.domain.shared.enums import AudioSource, SessionMode
from server.app.infrastructure.persistence.postgresql.repositories.postgresql_report_generation_job_repository import (
    PostgreSQLReportGenerationJobRepository,
)
from server.app.infrastructure.persistence.postgresql.repositories.session import (
    PostgreSQLSessionRepository,
)
from server.app.contexts.meeting import SessionService


def test_timestamptz_컬럼은_UTC_ISO_문자열로_돌아온다(isolated_database):
    with isolated_database.transaction() as connection:
        row = connection.execute(
            "SELECT TIMESTAMPTZ '2026-10-11 17:00:00+09' AS value"
        ).fetchone()

    assert row["value"] == "2026-10-11T08:00:00+00:00"


def test_offset이_다른_시각도_UTC_순서로_lease_만료를_판정한다(isolated_database):
    session_service = SessionService(PostgreSQLSessionRepository(isolated_database))
    session = session_service.create_session_draft(
        title="timestamptz 비교 테스트",
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
    # 첫 claim: lease는 UTC 00:05까지 유효하다.
    claimed = repository.claim_available(
        worker_id="worker-1",
        lease_expires_at="2026-10-11T00:05:00+00:00",
        claimed_at="2026-10-11T00:00:00+00:00",
        limit=1,
        max_attempts=3,
    )
    assert [item.id for item in claimed] == [job.id]

    # 서울 09:03 == UTC 00:03: 아직 유효하므로 claim되면 안 된다.
    # 문자열 비교였다면 "09:03" > "00:05"로 잘못 만료 처리됐을 것이다.
    still_leased = repository.claim_available(
        worker_id="worker-2",
        lease_expires_at="2026-10-11T00:15:00+00:00",
        claimed_at="2026-10-11T09:03:00+09:00",
        limit=1,
        max_attempts=3,
    )
    assert still_leased == []

    # 서울 09:06 == UTC 00:06: 만료됐으므로 claim된다.
    reclaimed = repository.claim_available(
        worker_id="worker-2",
        lease_expires_at="2026-10-11T00:16:00+00:00",
        claimed_at="2026-10-11T09:06:00+09:00",
        limit=1,
        max_attempts=3,
    )
    assert [item.id for item in reclaimed] == [job.id]
