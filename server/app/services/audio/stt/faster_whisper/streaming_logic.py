"""오디오 영역의 streaming logic 서비스를 제공한다."""
from __future__ import annotations

from server.app.services.audio.segmentation.speech_segmenter import SpeechSegment
from server.app.services.audio.stt.common.preview_stability import (
    longest_common_prefix,
    project_significant_prefix_to_text,
    significant_text,
    trim_to_commit_boundary,
)


def duration_ms_to_bytes(
    *,
    duration_ms: int,
    sample_rate_hz: int,
    sample_width_bytes: int,
    channels: int,
) -> int:
    """밀리초 구간을 PCM 바이트 길이로 환산한다."""

    bytes_per_second = sample_rate_hz * sample_width_bytes * channels
    return max(int(bytes_per_second * (duration_ms / 1000.0)), 1)


def build_preview_segment(
    *,
    raw_bytes: bytes,
    sample_rate_hz: int,
    sample_width_bytes: int,
    channels: int,
) -> SpeechSegment:
    """preview용 rolling buffer를 SpeechSegment로 감싼다."""

    frame_bytes = sample_rate_hz * sample_width_bytes * channels
    duration_ms = int(len(raw_bytes) / max(frame_bytes, 1) * 1000)
    return SpeechSegment(
        start_ms=0,
        end_ms=max(duration_ms, 1),
        raw_bytes=raw_bytes,
    )


def trim_buffer(buffer: bytearray, *, max_buffer_bytes: int) -> None:
    """rolling buffer 크기를 제한한다."""

    overflow = len(buffer) - max_buffer_bytes
    if overflow > 0:
        del buffer[:overflow]


def compute_stable_preview(
    *,
    preview_history: list[str],
    latest_preview: str,
    last_stable_preview: str,
    last_emitted_preview: str,
    agreement_min_count: int,
    min_stable_chars: int,
    min_growth_chars: int,
    backtrack_tolerance_chars: int,
    commit_min_chars_without_boundary: int,
) -> str:
    """preview history를 기반으로 안정된 partial 텍스트를 계산한다."""

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
        latest_preview,
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
    if len(significant_text(stable_preview)) < min_stable_chars:
        return ""

    if not is_meaningful_growth(
        stable_preview=stable_preview,
        last_emitted_preview=last_emitted_preview,
        min_growth_chars=min_growth_chars,
    ):
        return ""

    return stable_preview


def is_meaningful_growth(
    *,
    stable_preview: str,
    last_emitted_preview: str,
    min_growth_chars: int,
) -> bool:
    """새 stable preview가 실제로 의미 있는 전진인지 판단한다."""

    current_significant = significant_text(stable_preview)
    last_significant = significant_text(last_emitted_preview)
    if current_significant == last_significant:
        return False

    growth = len(current_significant) - len(last_significant)
    if growth >= min_growth_chars:
        return True

    if growth >= 0 and current_significant.startswith(last_significant):
        return True

    return False


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
