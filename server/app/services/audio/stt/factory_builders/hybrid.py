"""오디오 영역의 hybrid 서비스를 제공한다."""
from __future__ import annotations

from collections.abc import Callable

from server.app.services.audio.stt.transcription import SpeechToTextService, StreamingSpeechToTextService


def build_hybrid_local_streaming(
    *,
    create_service: Callable[..., SpeechToTextService],
    model_id: str,
    model_path: str | None,
    language: str | None,
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
    partial_backend_name: str | None,
    partial_model_id: str | None,
    partial_model_path: str | None,
    partial_device: str | None,
    partial_compute_type: str | None,
    partial_cpu_threads: int | None,
    partial_beam_size: int | None,
    final_backend_name: str | None,
    final_model_id: str | None,
    final_model_path: str | None,
    final_device: str | None,
    final_compute_type: str | None,
    final_cpu_threads: int | None,
    final_beam_size: int | None,
) -> SpeechToTextService:
    """로컬 preview/final 하이브리드 STT 서비스를 생성한다."""

    from server.app.services.audio.stt.hybrid_streaming_speech_to_text_service import (
        HybridStreamingConfig,
        HybridStreamingSpeechToTextService,
    )

    resolved_partial_backend_name = partial_backend_name or "faster_whisper_streaming"
    resolved_final_backend_name = final_backend_name or "faster_whisper"

    if resolved_partial_backend_name == "hybrid_local_streaming":
        raise ValueError("hybrid_local_streaming의 partial backend로 자신을 다시 지정할 수 없습니다.")
    if resolved_final_backend_name == "hybrid_local_streaming":
        raise ValueError("hybrid_local_streaming의 final backend로 자신을 다시 지정할 수 없습니다.")

    partial_service = create_service(
        backend_name=resolved_partial_backend_name,
        model_id=partial_model_id or model_id,
        model_path=partial_model_path or model_path,
        language=language,
        initial_prompt=None,
        device=partial_device or device,
        compute_type=partial_compute_type or compute_type,
        cpu_threads=partial_cpu_threads if partial_cpu_threads is not None else cpu_threads,
        beam_size=partial_beam_size if partial_beam_size is not None else beam_size,
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
    if not isinstance(partial_service, StreamingSpeechToTextService):
        raise TypeError("hybrid_local_streaming의 partial backend는 StreamingSpeechToTextService를 구현해야 합니다.")

    final_service = create_service(
        backend_name=resolved_final_backend_name,
        model_id=final_model_id or model_id,
        model_path=final_model_path or model_path,
        language=language,
        initial_prompt=None,
        device=final_device or device,
        compute_type=final_compute_type or compute_type,
        cpu_threads=final_cpu_threads if final_cpu_threads is not None else cpu_threads,
        beam_size=final_beam_size if final_beam_size is not None else beam_size,
        sample_rate_hz=sample_rate_hz,
        sample_width_bytes=sample_width_bytes,
        channels=channels,
        silence_rms_threshold=silence_rms_threshold,
    )
    if not isinstance(final_service, SpeechToTextService):
        raise TypeError("hybrid_local_streaming의 final backend는 SpeechToTextService를 구현해야 합니다.")

    return HybridStreamingSpeechToTextService(
        config=HybridStreamingConfig(reset_partial_stream_on_final=True),
        partial_service=partial_service,
        final_service=final_service,
    )
