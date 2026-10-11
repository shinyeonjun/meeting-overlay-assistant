"""control API와 live API가 분리된 상황의 세션 런타임 하트비트 테스트."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from server.app.domain.shared.enums import AudioSource, SessionMode, SessionStatus
from server.app.infrastructure.persistence.postgresql.repositories.session import (
    PostgreSQLSessionRepository,
)
from server.app.contexts.meeting import SessionRecoveryService
from server.app.contexts.meeting import SessionService

OLD_HEARTBEAT = "2000-01-01T00:00:00+00:00"


class _FakeLiveStreamService:
    """다른 프로세스의 live 런타임을 흉내낸다. 이 프로세스에는 컨텍스트가 없다."""

    def __init__(self, live_session_ids=()):
        self._live_session_ids = set(live_session_ids)

    def has_session_contexts(self, session_id: str) -> bool:
        return session_id in self._live_session_ids


def _start_session(isolated_database, title: str):
    session_repository = PostgreSQLSessionRepository(isolated_database)
    session_service = SessionService(session_repository)
    session = session_service.create_session_draft(
        title=title,
        mode=SessionMode.MEETING,
        source=AudioSource.SYSTEM_AUDIO,
    )
    session = session_service.start_session(session.id)
    return session_repository, session_service, session


def test_running으로_전이하는_순간_하트비트가_찍힌다(isolated_database):
    session_repository, _, session = _start_session(isolated_database, "하트비트 시작")

    assert session_repository.get_runtime_heartbeat_at(session.id) is not None


def test_ended로_전이하면_하트비트가_지워진다(isolated_database):
    session_repository, session_service, session = _start_session(isolated_database, "하트비트 종료")

    session_service.end_session(session.id)

    assert session_repository.get_runtime_heartbeat_at(session.id) is None


def test_touch는_running_세션만_갱신한다(isolated_database):
    session_repository, session_service, running = _start_session(isolated_database, "갱신 대상")
    draft = session_service.create_session_draft(
        title="초안",
        mode=SessionMode.MEETING,
        source=AudioSource.SYSTEM_AUDIO,
    )
    fresh = datetime.now(timezone.utc).isoformat()

    updated = session_repository.touch_runtime_heartbeat(
        [running.id, draft.id],
        heartbeat_at=fresh,
    )

    assert updated == 1
    assert session_repository.get_runtime_heartbeat_at(running.id) == fresh
    assert session_repository.get_runtime_heartbeat_at(draft.id) is None


def test_하트비트가_최근이면_다른_프로세스의_세션도_복구하지_않는다(isolated_database):
    session_repository, _, session = _start_session(isolated_database, "정상 live 세션")
    session_repository.touch_runtime_heartbeat(
        [session.id],
        heartbeat_at=datetime.now(timezone.utc).isoformat(),
    )
    recovery_service = SessionRecoveryService(
        session_repository=session_repository,
        live_stream_service=_FakeLiveStreamService(),
    )

    recovered_count = recovery_service.recover_orphaned_running_sessions()
    untouched = session_repository.get_by_id(session.id)

    assert recovered_count == 0
    assert untouched is not None
    assert untouched.status == SessionStatus.RUNNING


def test_하트비트가_오래되면_다른_프로세스의_세션도_복구한다(isolated_database):
    session_repository, _, session = _start_session(isolated_database, "끊긴 live 세션")
    session_repository.touch_runtime_heartbeat([session.id], heartbeat_at=OLD_HEARTBEAT)
    recovery_service = SessionRecoveryService(
        session_repository=session_repository,
        live_stream_service=_FakeLiveStreamService(),
    )

    recovered_count = recovery_service.recover_orphaned_running_sessions()
    recovered = session_repository.get_by_id(session.id)

    assert recovered_count == 1
    assert recovered is not None
    assert recovered.recovery_reason == "runtime_lost"


def test_같은_프로세스에_컨텍스트가_있으면_하트비트가_오래돼도_복구하지_않는다(isolated_database):
    session_repository, _, session = _start_session(isolated_database, "이 프로세스의 live 세션")
    session_repository.touch_runtime_heartbeat([session.id], heartbeat_at=OLD_HEARTBEAT)
    recovery_service = SessionRecoveryService(
        session_repository=session_repository,
        live_stream_service=_FakeLiveStreamService({session.id}),
    )

    assert recovery_service.recover_orphaned_running_sessions() == 0
    assert session_repository.get_by_id(session.id).status == SessionStatus.RUNNING


def test_mutation_직전_검사는_최근_하트비트를_존중한다(isolated_database):
    session_repository, _, session = _start_session(isolated_database, "수정 요청 대상")
    recovery_service = SessionRecoveryService(
        session_repository=session_repository,
        live_stream_service=_FakeLiveStreamService(),
    )
    session_repository.touch_runtime_heartbeat(
        [session.id],
        heartbeat_at=(datetime.now(timezone.utc) - timedelta(seconds=10)).isoformat(),
    )

    checked = recovery_service.recover_session_if_orphaned(session.id)

    assert checked is not None
    assert checked.status == SessionStatus.RUNNING


def test_하트비트_루프는_이_프로세스의_live_세션만_갱신한다():
    import asyncio
    from contextlib import suppress

    from server.app.contexts.meeting import (
        run_session_runtime_heartbeat,
    )

    class _LiveWithOneSession:
        def active_session_ids(self):
            return ["live-session"]

    class _RecordingRepository:
        def __init__(self) -> None:
            self.calls: list[tuple[list[str], str]] = []

        def touch_runtime_heartbeat(self, session_ids, *, heartbeat_at):
            self.calls.append((list(session_ids), heartbeat_at))
            return len(session_ids)

    repository = _RecordingRepository()

    async def run_for_a_moment() -> None:
        task = asyncio.create_task(
            run_session_runtime_heartbeat(
                live_stream_service=_LiveWithOneSession(),
                session_repository=repository,
                interval_seconds=0.01,
            )
        )
        await asyncio.sleep(0.1)
        task.cancel()
        with suppress(asyncio.CancelledError):
            await task

    asyncio.run(run_for_a_moment())

    assert repository.calls
    assert all(session_ids == ["live-session"] for session_ids, _ in repository.calls)
