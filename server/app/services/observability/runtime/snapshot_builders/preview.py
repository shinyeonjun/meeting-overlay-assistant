"""공통 영역의 preview 서비스를 제공한다."""
from __future__ import annotations

from server.app.services.observability.runtime.snapshot_builders.preview_helpers.cycle_selection import (
    build_preview_cycle_selection,
)
from server.app.services.observability.runtime.snapshot_builders.preview_helpers.event_groups import (
    build_preview_event_groups,
)
from server.app.services.observability.runtime.snapshot_builders.preview_helpers.payload import (
    build_preview_payload,
)
from server.app.services.observability.runtime.snapshot_builders.preview_helpers.timing import (
    build_preview_timing,
)


def build_preview_metrics(
    *,
    previews: list[dict[str, object]],
    preview_cycles: list[dict[str, object]],
) -> dict[str, object]:
    """preview 관련 metrics를 snapshot 필드로 계산한다."""

    groups = build_preview_event_groups(previews=previews, preview_cycles=preview_cycles)
    selection = build_preview_cycle_selection(groups)
    timing = build_preview_timing(groups, selection)
    return build_preview_payload(groups, selection, timing)
