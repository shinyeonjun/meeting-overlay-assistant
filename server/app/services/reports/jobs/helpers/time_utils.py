"""회의록 generation job 시간 helper."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone


def utc_now_iso() -> str:
    """현재 UTC 시각을 ISO 문자열로 반환한다."""

    return datetime.now(timezone.utc).isoformat()


def utc_after_seconds_iso(seconds: int) -> str:
    """현재 시각에서 lease 만료 시각을 ISO 문자열로 계산한다."""

    return (datetime.now(timezone.utc) + timedelta(seconds=max(seconds, 1))).isoformat()

