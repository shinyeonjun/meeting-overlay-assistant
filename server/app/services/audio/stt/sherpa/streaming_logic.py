"""sherpa-onnx preview/live_final 안정화 유틸리티."""

from __future__ import annotations

from server.app.services.audio.stt.common.preview_stability import (
    longest_common_prefix,
    project_significant_prefix_to_text,
    significant_text,
    trim_to_commit_boundary,
)


def compute_stable_preview(
    *,
    preview_history: list[str],
    latest_text: str,
    last_stable_preview: str,
    last_emitted_live_final: str,
    agreement_min_count: int,
    min_stable_chars: int,
    min_growth_chars: int,
    backtrack_tolerance_chars: int,
    commit_min_chars_without_boundary: int,
) -> str:
    """preview history를 기반으로 안정된 live_final 후보를 계산한다."""

    if len(preview_history) < agreement_min_count:
        return ""

    significant_history = [
        significant_text(value) for value in preview_history if value
    ]
    if len(significant_history) < agreement_min_count:
        return ""

    stable_significant = longest_common_prefix(significant_history)
    if len(stable_significant) < min_stable_chars:
        return ""

    projected_preview = project_significant_prefix_to_text(
        latest_text,
        len(stable_significant),
    )
    if not projected_preview:
        return ""

    committed_preview = trim_to_commit_boundary(
        projected_preview,
        commit_min_chars_without_boundary,
    )
    if len(significant_text(committed_preview)) < min_stable_chars:
        return ""

    stable_preview = merge_with_previous_stable_preview(
        committed_preview=committed_preview,
        last_stable_preview=last_stable_preview,
        backtrack_tolerance_chars=backtrack_tolerance_chars,
    )
    if not is_meaningful_growth(
        stable_preview=stable_preview,
        last_emitted_live_final=last_emitted_live_final,
        min_growth_chars=min_growth_chars,
    ):
        return ""

    return stable_preview


def merge_with_previous_stable_preview(
    *,
    committed_preview: str,
    last_stable_preview: str,
    backtrack_tolerance_chars: int,
) -> str:
    """작은 backtrack은 직전 stable preview를 유지한다."""

    if not last_stable_preview:
        return committed_preview

    previous_significant = significant_text(last_stable_preview)
    current_significant = significant_text(committed_preview)

    if current_significant.startswith(previous_significant):
        return committed_preview

    overlap = longest_common_prefix([previous_significant, current_significant])
    backtrack = len(previous_significant) - len(overlap)
    if backtrack <= backtrack_tolerance_chars:
        return last_stable_preview

    return committed_preview


def is_meaningful_growth(
    *,
    stable_preview: str,
    last_emitted_live_final: str,
    min_growth_chars: int,
) -> bool:
    """새 stable preview가 실제로 의미 있는 전진인지 판단한다."""

    current_significant = significant_text(stable_preview)
    last_significant = significant_text(last_emitted_live_final)
    if current_significant == last_significant:
        return False

    growth = len(current_significant) - len(last_significant)
    if growth >= min_growth_chars:
        return True

    return growth >= 0 and current_significant.startswith(last_significant)
