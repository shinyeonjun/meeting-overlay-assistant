"""Preview timing 계산 유틸."""

from __future__ import annotations

from dataclasses import dataclass

from server.app.services.observability.runtime.snapshot_builders.common import (
    first_epoch_ms,
    first_epoch_ms_at_or_after,
    last_epoch_ms_at_or_before,
)
from server.app.services.observability.runtime.snapshot_builders.preview_helpers.cycle_selection import (
    PreviewCycleSelection,
)
from server.app.services.observability.runtime.snapshot_builders.preview_helpers.event_groups import (
    PreviewEventGroups,
)


@dataclass(slots=True)
class PreviewTimingMetrics:
    """Preview 첫 productive cycle 기준 timing 묶음."""

    first_attempted_anchor_at_ms: int | None
    timeline_anchor_at_ms: int | None
    first_productive_gap_ms: int | None
    empty_cycles_before_first_candidate_count: int
    first_ready_at_ms: int | None
    first_job_started_at_ms: int | None
    first_picked_at_ms: int | None
    first_sherpa_non_empty_at_ms: int | None
    first_candidate_at_ms: int | None
    first_busy_skip_at_ms: int | None
    first_preferred_final_skip_at_ms: int | None


def build_preview_timing(
    groups: PreviewEventGroups,
    selection: PreviewCycleSelection,
) -> PreviewTimingMetrics:
    """첫 productive preview cycle의 timing을 계산한다."""

    first_preview_cycle = selection.first_preview_cycle
    first_ready_at_ms = (
        int(first_preview_cycle["ready_at_epoch_ms"])
        if first_preview_cycle is not None
        and isinstance(first_preview_cycle.get("ready_at_epoch_ms"), int)
        else last_epoch_ms_at_or_before(
            selection.preview_timing_ready,
            _resolve_picked_epoch_ms(first_preview_cycle, selection.preview_timing_picked),
        )
        or first_epoch_ms(selection.preview_timing_ready)
    )
    first_job_started_at_ms = (
        int(first_preview_cycle["job_started_at_epoch_ms"])
        if first_preview_cycle is not None
        and isinstance(first_preview_cycle.get("job_started_at_epoch_ms"), int)
        else first_epoch_ms(selection.preview_timing_job_started)
    )
    first_picked_at_ms = _resolve_picked_epoch_ms(
        first_preview_cycle,
        selection.preview_timing_picked,
        first_job_started_at_ms,
    )
    first_sherpa_non_empty_at_ms = (
        int(first_preview_cycle["sherpa_non_empty_at_epoch_ms"])
        if first_preview_cycle is not None
        and isinstance(first_preview_cycle.get("sherpa_non_empty_at_epoch_ms"), int)
        else first_epoch_ms_at_or_after(
            selection.preview_timing_sherpa_non_empty,
            first_job_started_at_ms,
        )
        or first_epoch_ms(selection.preview_timing_sherpa_non_empty)
    )
    first_candidate_at_ms = (
        int(first_preview_cycle["candidate_at_epoch_ms"])
        if first_preview_cycle is not None
        and isinstance(first_preview_cycle.get("candidate_at_epoch_ms"), int)
        else first_epoch_ms_at_or_after(
            selection.preview_timing_candidates,
            first_sherpa_non_empty_at_ms,
        )
        or first_epoch_ms_at_or_after(
            selection.preview_timing_candidates,
            first_job_started_at_ms,
        )
        or first_epoch_ms(selection.preview_timing_candidates)
    )
    first_busy_skip_at_ms = first_epoch_ms(groups.preview_busy_skips)
    first_preferred_final_skip_at_ms = first_epoch_ms(groups.preview_preferred_final_skips)
    first_attempted_anchor_at_ms = (
        int(selection.first_attempted_preview_cycle["anchor_epoch_ms"])
        if selection.first_attempted_preview_cycle is not None
        and isinstance(selection.first_attempted_preview_cycle.get("anchor_epoch_ms"), int)
        else None
    )
    timeline_anchor_at_ms = min(
        (
            epoch_ms
            for epoch_ms in (
                first_ready_at_ms,
                first_picked_at_ms,
                first_job_started_at_ms,
                first_sherpa_non_empty_at_ms,
                first_candidate_at_ms,
                first_busy_skip_at_ms,
                first_preferred_final_skip_at_ms,
            )
            if epoch_ms is not None
        ),
        default=None,
    )
    empty_cycles_before_first_candidate_count = sum(
        1
        for item in groups.preview_cycles_with_anchor
        if first_attempted_anchor_at_ms is not None
        and timeline_anchor_at_ms is not None
        and isinstance(item.get("anchor_epoch_ms"), int)
        and first_attempted_anchor_at_ms <= int(item["anchor_epoch_ms"]) < timeline_anchor_at_ms
        and not isinstance(item.get("candidate_at_epoch_ms"), int)
    )

    return PreviewTimingMetrics(
        first_attempted_anchor_at_ms=first_attempted_anchor_at_ms,
        timeline_anchor_at_ms=timeline_anchor_at_ms,
        first_productive_gap_ms=(
            max(timeline_anchor_at_ms - first_attempted_anchor_at_ms, 0)
            if timeline_anchor_at_ms is not None and first_attempted_anchor_at_ms is not None
            else None
        ),
        empty_cycles_before_first_candidate_count=empty_cycles_before_first_candidate_count,
        first_ready_at_ms=first_ready_at_ms,
        first_job_started_at_ms=first_job_started_at_ms,
        first_picked_at_ms=first_picked_at_ms,
        first_sherpa_non_empty_at_ms=first_sherpa_non_empty_at_ms,
        first_candidate_at_ms=first_candidate_at_ms,
        first_busy_skip_at_ms=first_busy_skip_at_ms,
        first_preferred_final_skip_at_ms=first_preferred_final_skip_at_ms,
    )


def _resolve_picked_epoch_ms(
    first_preview_cycle: dict[str, object] | None,
    preview_timing_picked: list[dict[str, object]],
    job_started_at_ms: int | None = None,
) -> int | None:
    """첫 picked 시각을 계산한다."""

    if first_preview_cycle is not None and isinstance(first_preview_cycle.get("picked_at_epoch_ms"), int):
        return int(first_preview_cycle["picked_at_epoch_ms"])
    return last_epoch_ms_at_or_before(preview_timing_picked, job_started_at_ms) or first_epoch_ms(
        preview_timing_picked
    )
