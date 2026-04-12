"""오디오 영역의 streaming 서비스를 제공한다."""
from __future__ import annotations

from server.app.services.audio.stt.factory_builders import (
    build_faster_whisper_streaming,
    build_moonshine_streaming,
    build_sherpa_onnx_streaming,
)
from server.app.services.audio.stt.transcription import SpeechToTextService


def build_faster_whisper_streaming_compat(
    *,
    model_id: str,
    model_path: str | None,
    language: str | None,
    initial_prompt: str | None,
    device: str,
    compute_type: str,
    cpu_threads: int,
    beam_size: int,
    sample_rate_hz: int,
    sample_width_bytes: int,
    channels: int,
    silence_rms_threshold: float,
    partial_buffer_ms: int,
    partial_emit_interval_ms: int,
    partial_min_rms_threshold: float,
    partial_agreement_window: int,
    partial_agreement_min_count: int,
    partial_min_stable_chars: int,
    partial_min_growth_chars: int,
    partial_backtrack_tolerance_chars: int,
    partial_commit_min_chars_without_boundary: int,
) -> SpeechToTextService:
    """기존 Faster Whisper streaming builder 호환 wrapper."""

    return build_faster_whisper_streaming(
        model_id=model_id,
        model_path=model_path,
        language=language,
        initial_prompt=initial_prompt,
        device=device,
        compute_type=compute_type,
        cpu_threads=cpu_threads,
        beam_size=beam_size,
        sample_rate_hz=sample_rate_hz,
        sample_width_bytes=sample_width_bytes,
        channels=channels,
        silence_rms_threshold=silence_rms_threshold,
        partial_buffer_ms=partial_buffer_ms,
        partial_emit_interval_ms=partial_emit_interval_ms,
        partial_min_rms_threshold=partial_min_rms_threshold,
        partial_agreement_window=partial_agreement_window,
        partial_agreement_min_count=partial_agreement_min_count,
        partial_min_stable_chars=partial_min_stable_chars,
        partial_min_growth_chars=partial_min_growth_chars,
        partial_backtrack_tolerance_chars=partial_backtrack_tolerance_chars,
        partial_commit_min_chars_without_boundary=partial_commit_min_chars_without_boundary,
    )


def build_sherpa_onnx_streaming_compat(
    *,
    model_id: str,
    model_path: str | None,
    language: str | None,
    device: str,
    cpu_threads: int,
    beam_size: int,
    sample_rate_hz: int,
    sample_width_bytes: int,
    channels: int,
    partial_emit_interval_ms: int,
    partial_agreement_window: int,
    partial_agreement_min_count: int,
    partial_min_stable_chars: int,
    partial_min_growth_chars: int,
    partial_backtrack_tolerance_chars: int,
    partial_commit_min_chars_without_boundary: int,
) -> SpeechToTextService:
    """기존 Sherpa ONNX streaming builder 호환 wrapper."""

    return build_sherpa_onnx_streaming(
        model_id=model_id,
        model_path=model_path,
        language=language,
        device=device,
        cpu_threads=cpu_threads,
        beam_size=beam_size,
        sample_rate_hz=sample_rate_hz,
        sample_width_bytes=sample_width_bytes,
        channels=channels,
        partial_emit_interval_ms=partial_emit_interval_ms,
        partial_agreement_window=partial_agreement_window,
        partial_agreement_min_count=partial_agreement_min_count,
        partial_min_stable_chars=partial_min_stable_chars,
        partial_min_growth_chars=partial_min_growth_chars,
        partial_backtrack_tolerance_chars=partial_backtrack_tolerance_chars,
        partial_commit_min_chars_without_boundary=partial_commit_min_chars_without_boundary,
    )


def build_moonshine_streaming_compat(
    *,
    model_id: str,
    model_path: str | None,
    language: str | None,
    sample_rate_hz: int,
    sample_width_bytes: int,
    channels: int,
    silence_rms_threshold: float,
    partial_buffer_ms: int,
    partial_emit_interval_ms: int,
    partial_min_rms_threshold: float,
    partial_agreement_window: int,
    partial_agreement_min_count: int,
    partial_min_stable_chars: int,
    partial_min_growth_chars: int,
) -> SpeechToTextService:
    """기존 Moonshine streaming builder 호환 wrapper."""

    return build_moonshine_streaming(
        model_id=model_id,
        model_path=model_path,
        language=language,
        sample_rate_hz=sample_rate_hz,
        sample_width_bytes=sample_width_bytes,
        channels=channels,
        silence_rms_threshold=silence_rms_threshold,
        partial_buffer_ms=partial_buffer_ms,
        partial_emit_interval_ms=partial_emit_interval_ms,
        partial_min_rms_threshold=partial_min_rms_threshold,
        partial_agreement_window=partial_agreement_window,
        partial_agreement_min_count=partial_agreement_min_count,
        partial_min_stable_chars=partial_min_stable_chars,
        partial_min_growth_chars=partial_min_growth_chars,
    )
