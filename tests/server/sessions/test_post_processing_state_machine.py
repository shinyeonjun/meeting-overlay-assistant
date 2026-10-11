"""후처리 상태 전이 규칙과 세션 상태와의 불변식을 도메인 수준에서 검증한다."""

from __future__ import annotations

import pytest

from server.app.domain.session import MeetingSession
from server.app.domain.shared.enums import AudioSource, PostProcessingStatus, SessionMode

P = PostProcessingStatus


def _ended_session() -> MeetingSession:
    return (
        MeetingSession.create_draft(
            title="상태 기계 테스트",
            mode=SessionMode.MEETING,
            source=AudioSource.SYSTEM_AUDIO,
        )
        .start_running()
        .end()
    )


def test_정상_흐름은_대기_처리_완료로_간다():
    session = _ended_session()

    queued = session.queue_post_processing()
    processing = queued.mark_post_processing_started()
    completed = processing.mark_post_processing_completed()

    assert queued.post_processing_status == P.QUEUED
    assert processing.post_processing_status == P.PROCESSING
    assert completed.post_processing_status == P.COMPLETED
    assert completed.canonical_transcript_version == 1


def test_회의가_끝나기_전에는_후처리를_요청할_수_없다():
    draft = MeetingSession.create_draft(
        title="진행 중",
        mode=SessionMode.MEETING,
        source=AudioSource.SYSTEM_AUDIO,
    )

    with pytest.raises(ValueError, match="회의가 끝난 뒤"):
        draft.queue_post_processing()

    running = draft.start_running()
    with pytest.raises(ValueError, match="회의가 끝난 뒤"):
        running.mark_post_processing_started()


def test_처리되지_않은_상태에서_바로_완료할_수_없다():
    queued = _ended_session().queue_post_processing()

    with pytest.raises(ValueError, match="queued에서 completed"):
        queued.mark_post_processing_completed()


def test_완료된_후처리는_다시_처리중으로_되돌릴_수_없다():
    completed = _ended_session().queue_post_processing().mark_post_processing_started().mark_post_processing_completed()

    with pytest.raises(ValueError, match="completed에서 processing"):
        completed.mark_post_processing_started()


def test_완료된_후처리에_재요청은_허용된다():
    completed = _ended_session().queue_post_processing().mark_post_processing_started().mark_post_processing_completed()

    requeued = completed.queue_post_processing()

    assert requeued.post_processing_status == P.QUEUED


def test_대기_중_재요청은_멱등이다():
    queued = _ended_session().queue_post_processing()

    assert queued.queue_post_processing().post_processing_status == P.QUEUED


def test_완료_후_하류_등록_실패는_보상으로_failed가_된다():
    completed = _ended_session().queue_post_processing().mark_post_processing_started().mark_post_processing_completed()

    failed = completed.mark_post_processing_failed("노트 보정 등록 실패")

    assert failed.post_processing_status == P.FAILED
    assert failed.post_processing_error_message == "노트 보정 등록 실패"


def test_상태_문자열과_비교가_그대로_된다():
    session = _ended_session().queue_post_processing()

    assert session.post_processing_status == "queued"
    assert P("queued") is P.QUEUED
