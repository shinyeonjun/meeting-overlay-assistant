"""시간 헬퍼. 서버 전체가 같은 형식의 현재 시각을 쓰도록 한 곳에 둔다."""

from __future__ import annotations

from datetime import datetime, timezone
from time import time


def utc_now_iso() -> str:
    """현재 UTC 시각을 ISO 문자열로 돌려준다."""

    return datetime.now(timezone.utc).isoformat()


def utc_now_epoch_ms() -> int:
    """현재 시각을 epoch 밀리초 정수로 돌려준다."""

    return int(time() * 1000)
