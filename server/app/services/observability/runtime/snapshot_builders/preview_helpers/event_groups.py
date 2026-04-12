"""공통 영역의 event groups 서비스를 제공한다."""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True)
class PreviewEventGroups:
    """Preview reducer가 자주 쓰는 이벤트 그룹 묶음."""

    preview_candidates: list[dict[str, object]]
    preview_emitted: list[dict[str, object]]
    preview_rejected: list[dict[str, object]]
    preview_backpressure: list[dict[str, object]]
    preview_ready: list[dict[str, object]]
    preview_picked: list[dict[str, object]]
    preview_skips: list[dict[str, object]]
    preview_busy_skips: list[dict[str, object]]
    preview_preferred_final_skips: list[dict[str, object]]
    preview_job_started: list[dict[str, object]]
    preview_sherpa_non_empty: list[dict[str, object]]
    preview_cycles_with_anchor: list[dict[str, object]]
    preview_cycles_with_candidate: list[dict[str, object]]
    preview_cycles_with_emitted: list[dict[str, object]]


def build_preview_event_groups(
    *,
    previews: list[dict[str, object]],
    preview_cycles: list[dict[str, object]],
) -> PreviewEventGroups:
    """Preview 이벤트를 의미별로 미리 묶는다."""

    preview_candidates = [item for item in previews if item.get("event_type") == "candidate"]
    preview_emitted = [item for item in previews if item.get("event_type") == "emitted"]
    preview_rejected = [item for item in previews if item.get("event_type") == "rejected"]
    preview_backpressure = [item for item in previews if item.get("event_type") == "backpressure"]
    preview_ready = [item for item in previews if item.get("event_type") == "ready"]
    preview_picked = [item for item in previews if item.get("event_type") == "picked"]
    preview_skips = [item for item in previews if item.get("event_type") == "skip"]
    preview_job_started = [item for item in previews if item.get("event_type") == "job_started"]
    preview_sherpa_non_empty = [
        item for item in previews if item.get("event_type") == "sherpa_non_empty"
    ]
    preview_cycles_with_anchor = [
        item for item in preview_cycles if isinstance(item.get("anchor_epoch_ms"), int)
    ]
    preview_cycles_with_candidate = [
        item
        for item in preview_cycles_with_anchor
        if isinstance(item.get("candidate_at_epoch_ms"), int)
    ]
    preview_cycles_with_emitted = [
        item
        for item in preview_cycles_with_anchor
        if isinstance(item.get("emitted_at_epoch_ms"), int)
    ]
    return PreviewEventGroups(
        preview_candidates=preview_candidates,
        preview_emitted=preview_emitted,
        preview_rejected=preview_rejected,
        preview_backpressure=preview_backpressure,
        preview_ready=preview_ready,
        preview_picked=preview_picked,
        preview_skips=preview_skips,
        preview_busy_skips=[item for item in preview_skips if item.get("reason") == "busy"],
        preview_preferred_final_skips=[
            item for item in preview_skips if item.get("reason") == "preferred_final"
        ],
        preview_job_started=preview_job_started,
        preview_sherpa_non_empty=preview_sherpa_non_empty,
        preview_cycles_with_anchor=preview_cycles_with_anchor,
        preview_cycles_with_candidate=preview_cycles_with_candidate,
        preview_cycles_with_emitted=preview_cycles_with_emitted,
    )
