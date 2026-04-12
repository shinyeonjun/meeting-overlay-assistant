"""런타임 관측성 계산에 쓰는 공용 시간 헬퍼."""

from __future__ import annotations

from datetime import datetime, timezone
import time


def utc_now_iso() -> str:
    """현재 UTC 시각을 ISO 문자열로 반환한다."""

    return datetime.now(timezone.utc).isoformat()


def utc_now_epoch_ms() -> int:
    """현재 UTC epoch millisecond를 반환한다."""

    return int(time.time() * 1000)


def relative_epoch_ms(*, absolute_epoch_ms: int | None, anchor_epoch_ms: int | None) -> int | None:
    """anchor 기준 상대 millisecond를 계산한다."""

    if absolute_epoch_ms is None or anchor_epoch_ms is None:
        return None
    return max(absolute_epoch_ms - anchor_epoch_ms, 0)
