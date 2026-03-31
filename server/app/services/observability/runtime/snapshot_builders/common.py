"""Runtime snapshot 공통 계산 유틸리티."""

from __future__ import annotations


def filter_by_preview_cycle_id(
    items: list[dict[str, object]],
    preview_cycle_id: int | None,
) -> list[dict[str, object]]:
    """특정 preview cycle에 속한 이벤트만 남긴다."""

    if preview_cycle_id is None:
        return items
    return [item for item in items if item.get("preview_cycle_id") == preview_cycle_id]


def first_epoch_ms(items: list[dict[str, object]]) -> int | None:
    """recorded_at_epoch_ms의 최소값을 반환한다."""

    epoch_values = [
        int(item["recorded_at_epoch_ms"])
        for item in items
        if isinstance(item.get("recorded_at_epoch_ms"), int)
    ]
    if not epoch_values:
        return None
    return min(epoch_values)


def first_stage_value(
    items: list[dict[str, object]],
    key: str,
) -> object | None:
    """가장 이른 stage 이벤트의 특정 필드를 반환한다."""

    earliest_item = min(
        (
            item
            for item in items
            if isinstance(item.get("recorded_at_epoch_ms"), int)
        ),
        key=lambda item: int(item["recorded_at_epoch_ms"]),
        default=None,
    )
    if earliest_item is None:
        return None
    return earliest_item.get(key)


def last_epoch_ms_at_or_before(
    items: list[dict[str, object]],
    boundary_epoch_ms: int | None,
) -> int | None:
    """경계 시각 이하의 가장 마지막 epoch를 반환한다."""

    if boundary_epoch_ms is None:
        return None
    epoch_values = sorted(
        int(item["recorded_at_epoch_ms"])
        for item in items
        if isinstance(item.get("recorded_at_epoch_ms"), int)
        and int(item["recorded_at_epoch_ms"]) <= boundary_epoch_ms
    )
    if not epoch_values:
        return None
    return epoch_values[-1]


def first_epoch_ms_at_or_after(
    items: list[dict[str, object]],
    boundary_epoch_ms: int | None,
) -> int | None:
    """경계 시각 이상의 가장 이른 epoch를 반환한다."""

    if boundary_epoch_ms is None:
        return None
    epoch_values = sorted(
        int(item["recorded_at_epoch_ms"])
        for item in items
        if isinstance(item.get("recorded_at_epoch_ms"), int)
        and int(item["recorded_at_epoch_ms"]) >= boundary_epoch_ms
    )
    if not epoch_values:
        return None
    return epoch_values[0]
