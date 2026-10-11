"""진행 중 회의의 살아 있음 판단 정책 (DB 없음)."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from server.app.domain.session.runtime_liveness import RuntimeLivenessPolicy
from server.app.domain.shared.enums import SessionStatus

NOW = datetime(2026, 10, 11, 12, 0, tzinfo=timezone.utc)
POLICY = RuntimeLivenessPolicy(stale_after=timedelta(seconds=90))


def _orphaned(**overrides) -> bool:
    values = dict(
        status=SessionStatus.RUNNING,
        has_local_context=False,
        last_heartbeat_at=(NOW - timedelta(seconds=10)).isoformat(),
        now=NOW,
    )
    values.update(overrides)
    return POLICY.is_orphaned(**values)


def test_최근_하트비트가_있으면_고아가_아니다():
    assert _orphaned() is False


def test_같은_프로세스에_컨텍스트가_있으면_고아가_아니다():
    assert _orphaned(has_local_context=True, last_heartbeat_at=None) is False


def test_하트비트가_기준보다_오래되면_고아다():
    stale = (NOW - timedelta(seconds=91)).isoformat()

    assert _orphaned(last_heartbeat_at=stale) is True


def test_하트비트가_정확히_기준이면_고아다():
    boundary = (NOW - timedelta(seconds=90)).isoformat()

    assert _orphaned(last_heartbeat_at=boundary) is True


def test_하트비트가_없으면_고아다():
    assert _orphaned(last_heartbeat_at=None) is True


def test_running이_아니면_고아가_아니다():
    assert _orphaned(status=SessionStatus.ENDED, last_heartbeat_at=None) is False
    assert _orphaned(status=SessionStatus.DRAFT, last_heartbeat_at=None) is False


def test_다른_offset_표기도_UTC_기준으로_판단한다():
    # 서울 21:55 == UTC 12:55: 기준(11:58:30) 이후이므로 살아 있다.
    seoul = "2026-10-11T21:55:00+09:00"

    assert _orphaned(last_heartbeat_at=seoul) is False
