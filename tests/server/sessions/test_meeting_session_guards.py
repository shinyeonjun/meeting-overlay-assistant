"""진행 중 세션의 삭제/재생성 금지 규칙은 도메인 객체가 직접 검사한다."""

from __future__ import annotations

import pytest

from server.app.domain.session import MeetingSession
from server.app.domain.shared.enums import AudioSource, SessionMode


def _draft() -> MeetingSession:
    return MeetingSession.create_draft(
        title="가드 테스트",
        mode=SessionMode.MEETING,
        source=AudioSource.SYSTEM_AUDIO,
    )


def test_draft는_삭제와_재생성이_가능하다():
    session = _draft()

    session.ensure_deletable()
    session.ensure_reprocessable()


def test_running_세션은_삭제할_수_없다():
    session = _draft().start_running()

    with pytest.raises(ValueError, match="먼저 종료해야 삭제"):
        session.ensure_deletable()


def test_running_세션은_재생성할_수_없다():
    session = _draft().start_running()

    with pytest.raises(ValueError, match="노트를 다시 만들 수 없습니다"):
        session.ensure_reprocessable()


def test_ended_세션은_삭제와_재생성이_가능하다():
    session = _draft().start_running().end()

    session.ensure_deletable()
    session.ensure_reprocessable()
