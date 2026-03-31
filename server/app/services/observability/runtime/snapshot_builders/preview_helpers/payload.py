"""Preview metrics payload 조립 유틸."""

from __future__ import annotations

from server.app.services.observability.runtime.metrics_helpers import relative_epoch_ms
from server.app.services.observability.runtime.snapshot_builders.common import first_stage_value
from server.app.services.observability.runtime.snapshot_builders.preview_helpers.cycle_selection import (
    PreviewCycleSelection,
)
from server.app.services.observability.runtime.snapshot_builders.preview_helpers.event_groups import (
    PreviewEventGroups,
)
from server.app.services.observability.runtime.snapshot_builders.preview_helpers.timing import (
    PreviewTimingMetrics,
)


def build_preview_payload(
    groups: PreviewEventGroups,
    selection: PreviewCycleSelection,
    timing: PreviewTimingMetrics,
) -> dict[str, object]:
    """Preview metrics 응답 payload를 조립한다."""

    first_preview_cycle = selection.first_preview_cycle
    return {
        "preview_candidate_count": len(groups.preview_candidates),
        "preview_candidate_preview_count": sum(
            1 for item in groups.preview_candidates if item.get("kind") == "preview"
        ),
        "preview_candidate_live_final_count": sum(
            1 for item in groups.preview_candidates if item.get("kind") == "live_final"
        ),
        "preview_first_attempted_anchor_at_ms": timing.first_attempted_anchor_at_ms,
        "preview_timeline_anchor_at_ms": timing.timeline_anchor_at_ms,
        "preview_first_productive_gap_ms": timing.first_productive_gap_ms,
        "preview_empty_cycles_before_first_candidate_count": timing.empty_cycles_before_first_candidate_count,
        "preview_first_ready_at_ms": timing.first_ready_at_ms,
        "preview_first_job_started_at_ms": timing.first_job_started_at_ms,
        "preview_first_picked_at_ms": timing.first_picked_at_ms,
        "preview_first_sherpa_non_empty_at_ms": timing.first_sherpa_non_empty_at_ms,
        "preview_first_candidate_at_ms": timing.first_candidate_at_ms,
        "preview_first_ready_relative_ms": relative_epoch_ms(
            absolute_epoch_ms=timing.first_ready_at_ms,
            anchor_epoch_ms=timing.timeline_anchor_at_ms,
        ),
        "preview_first_job_started_relative_ms": relative_epoch_ms(
            absolute_epoch_ms=timing.first_job_started_at_ms,
            anchor_epoch_ms=timing.timeline_anchor_at_ms,
        ),
        "preview_first_picked_relative_ms": relative_epoch_ms(
            absolute_epoch_ms=timing.first_picked_at_ms,
            anchor_epoch_ms=timing.timeline_anchor_at_ms,
        ),
        "preview_first_sherpa_non_empty_relative_ms": relative_epoch_ms(
            absolute_epoch_ms=timing.first_sherpa_non_empty_at_ms,
            anchor_epoch_ms=timing.timeline_anchor_at_ms,
        ),
        "preview_first_candidate_relative_ms": relative_epoch_ms(
            absolute_epoch_ms=timing.first_candidate_at_ms,
            anchor_epoch_ms=timing.timeline_anchor_at_ms,
        ),
        "preview_first_ready_pending_final_chunk_count": (
            first_preview_cycle.get("ready_pending_final_chunk_count")
            if first_preview_cycle is not None
            else first_stage_value(selection.preview_timing_ready, "pending_final_chunk_count")
        ),
        "preview_first_ready_busy_worker_count": (
            first_preview_cycle.get("ready_busy_worker_count")
            if first_preview_cycle is not None
            else first_stage_value(selection.preview_timing_ready, "busy_worker_count")
        ),
        "preview_first_picked_pending_final_chunk_count": (
            first_preview_cycle.get("picked_pending_final_chunk_count")
            if first_preview_cycle is not None
            else first_stage_value(selection.preview_timing_picked, "pending_final_chunk_count")
        ),
        "preview_first_picked_busy_worker_count": (
            first_preview_cycle.get("picked_busy_worker_count")
            if first_preview_cycle is not None
            else first_stage_value(selection.preview_timing_picked, "busy_worker_count")
        ),
        "preview_notify_skipped_busy_count": len(groups.preview_busy_skips),
        "preview_notify_skipped_preferred_final_count": len(groups.preview_preferred_final_skips),
        "preview_first_busy_skip_at_ms": timing.first_busy_skip_at_ms,
        "preview_first_preferred_final_skip_at_ms": timing.first_preferred_final_skip_at_ms,
        "preview_first_busy_skip_relative_ms": relative_epoch_ms(
            absolute_epoch_ms=timing.first_busy_skip_at_ms,
            anchor_epoch_ms=timing.timeline_anchor_at_ms,
        ),
        "preview_first_preferred_final_skip_relative_ms": relative_epoch_ms(
            absolute_epoch_ms=timing.first_preferred_final_skip_at_ms,
            anchor_epoch_ms=timing.timeline_anchor_at_ms,
        ),
        "preview_first_busy_skip_pending_final_chunk_count": first_stage_value(
            groups.preview_busy_skips,
            "pending_final_chunk_count",
        ),
        "preview_first_busy_skip_has_pending_preview_chunk": first_stage_value(
            groups.preview_busy_skips,
            "has_pending_preview_chunk",
        ),
        "preview_first_busy_skip_busy_worker_count": first_stage_value(
            groups.preview_busy_skips,
            "busy_worker_count",
        ),
        "preview_first_busy_skip_busy_job_kind": first_stage_value(
            groups.preview_busy_skips,
            "busy_job_kind",
        ),
        "preview_first_preferred_final_skip_pending_final_chunk_count": first_stage_value(
            groups.preview_preferred_final_skips,
            "pending_final_chunk_count",
        ),
        "preview_first_preferred_final_skip_has_pending_preview_chunk": first_stage_value(
            groups.preview_preferred_final_skips,
            "has_pending_preview_chunk",
        ),
        "preview_first_preferred_final_skip_busy_worker_count": first_stage_value(
            groups.preview_preferred_final_skips,
            "busy_worker_count",
        ),
        "preview_first_preferred_final_skip_busy_job_kind": first_stage_value(
            groups.preview_preferred_final_skips,
            "busy_job_kind",
        ),
        "preview_emitted_count": len(groups.preview_emitted),
        "preview_emitted_preview_count": sum(
            1 for item in groups.preview_emitted if item.get("kind") == "preview"
        ),
        "preview_emitted_live_final_count": sum(
            1 for item in groups.preview_emitted if item.get("kind") == "live_final"
        ),
        "preview_guard_rejected_count": sum(
            1 for item in groups.preview_rejected if item.get("filter_stage") == "guard"
        ),
        "preview_length_rejected_count": sum(
            1 for item in groups.preview_rejected if item.get("filter_stage") == "length"
        ),
        "preview_backpressure_count": len(groups.preview_backpressure),
    }
