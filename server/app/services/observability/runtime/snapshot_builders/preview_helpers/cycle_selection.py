"""Preview cycle 선택 유틸."""

from __future__ import annotations

from dataclasses import dataclass

from server.app.services.observability.runtime.snapshot_builders.common import (
    filter_by_preview_cycle_id,
)
from server.app.services.observability.runtime.snapshot_builders.preview_helpers.event_groups import (
    PreviewEventGroups,
)


@dataclass(slots=True)
class PreviewCycleSelection:
    """첫 productive preview cycle 기준으로 묶은 선택 결과."""

    first_attempted_preview_cycle: dict[str, object] | None
    first_preview_cycle: dict[str, object] | None
    first_preview_cycle_id: int | None
    preview_timing_ready: list[dict[str, object]]
    preview_timing_picked: list[dict[str, object]]
    preview_timing_job_started: list[dict[str, object]]
    preview_timing_sherpa_non_empty: list[dict[str, object]]
    preview_timing_candidates: list[dict[str, object]]


def build_preview_cycle_selection(groups: PreviewEventGroups) -> PreviewCycleSelection:
    """첫 attempted/productive preview cycle과 해당 이벤트를 고른다."""

    first_attempted_preview_cycle = min(
        groups.preview_cycles_with_anchor,
        key=lambda item: int(item["anchor_epoch_ms"]),
        default=None,
    )
    first_preview_cycle = min(
        groups.preview_cycles_with_candidate,
        key=lambda item: int(item["candidate_at_epoch_ms"]),
        default=None,
    )
    if first_preview_cycle is None:
        first_preview_cycle = min(
            groups.preview_cycles_with_emitted,
            key=lambda item: int(item["emitted_at_epoch_ms"]),
            default=None,
        )
    if first_preview_cycle is None:
        first_preview_cycle = first_attempted_preview_cycle

    first_preview_cycle_id = (
        int(first_preview_cycle["preview_cycle_id"])
        if first_preview_cycle is not None
        and isinstance(first_preview_cycle.get("preview_cycle_id"), int)
        else None
    )
    return PreviewCycleSelection(
        first_attempted_preview_cycle=first_attempted_preview_cycle,
        first_preview_cycle=first_preview_cycle,
        first_preview_cycle_id=first_preview_cycle_id,
        preview_timing_ready=filter_by_preview_cycle_id(
            groups.preview_ready,
            first_preview_cycle_id,
        ),
        preview_timing_picked=filter_by_preview_cycle_id(
            groups.preview_picked,
            first_preview_cycle_id,
        ),
        preview_timing_job_started=filter_by_preview_cycle_id(
            groups.preview_job_started,
            first_preview_cycle_id,
        ),
        preview_timing_sherpa_non_empty=filter_by_preview_cycle_id(
            groups.preview_sherpa_non_empty,
            first_preview_cycle_id,
        ),
        preview_timing_candidates=filter_by_preview_cycle_id(
            groups.preview_candidates,
            first_preview_cycle_id,
        ),
    )
