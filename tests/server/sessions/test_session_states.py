"""MeetingSession의 하위 상태(복구, 후처리) 값 객체 구조를 검증한다."""

from __future__ import annotations

from server.app.domain.session import MeetingSession
from server.app.domain.session.session_states import PostProcessingState, RecoveryState
from server.app.domain.shared.enums import AudioSource, PostProcessingStatus, SessionMode

P = PostProcessingStatus


def _ended() -> MeetingSession:
    return MeetingSession.create_draft(
        title="상태 분할 테스트",
        mode=SessionMode.MEETING,
        source=AudioSource.SYSTEM_AUDIO,
    ).start_running().end()


def test_새_세션의_하위_상태는_기본값이다():
    session = _ended()

    assert session.recovery == RecoveryState()
    assert session.post_processing == PostProcessingState()
    assert session.post_processing_status == P.NOT_STARTED


def test_복구_표시는_후처리_상태를_건드리지_않는다():
    session = _ended().queue_post_processing()

    recovering = session.mark_recovery_required("runtime_lost")

    assert recovering.recovery_required is True
    assert recovering.recovery_reason == "runtime_lost"
    assert recovering.post_processing_status == P.QUEUED


def test_후처리를_요청하면_복구_표시가_해제된다():
    recovering = _ended().mark_recovery_required("runtime_lost")

    queued = recovering.queue_post_processing()

    assert queued.recovery == RecoveryState()
    assert queued.post_processing_status == P.QUEUED


def test_정본_버전은_후처리_완료마다_올라간다():
    session = _ended().queue_post_processing().mark_post_processing_started()

    completed = session.mark_post_processing_completed()

    assert completed.canonical_transcript_version == 1
    assert completed.canonical_events_version == 1
    assert completed.post_processing.canonical_transcript_version == 1


def test_읽기_속성은_하위_객체_값과_같다():
    session = _ended().queue_post_processing()

    assert session.post_processing_requested_at == session.post_processing.requested_at
    assert session.canonical_transcript_version == session.post_processing.canonical_transcript_version
