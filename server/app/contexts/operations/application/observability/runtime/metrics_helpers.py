"""런타임 관측성 계산에 쓰는 공용 시간 헬퍼."""

from __future__ import annotations

from server.app.core.clock import utc_now_epoch_ms, utc_now_iso  # noqa: F401 (기존 import 경로 호환)


def relative_epoch_ms(*, absolute_epoch_ms: int | None, anchor_epoch_ms: int | None) -> int | None:
    """anchor 기준 상대 millisecond를 계산한다."""

    if absolute_epoch_ms is None or anchor_epoch_ms is None:
        return None
    return max(absolute_epoch_ms - anchor_epoch_ms, 0)
