"""스트리밍 STT 서비스 빌더."""

from __future__ import annotations

from pathlib import Path

from server.app.services.audio.stt.transcription import SpeechToTextService


def build_faster_whisper_streaming(
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
    vad_filter: bool,
    vad_min_silence_duration_ms: int | None,
    vad_speech_pad_ms: int | None,
    no_speech_threshold: float | None,
    condition_on_previous_text: bool,
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
    """Faster Whisper 스트리밍 서비스를 생성한다."""

    from server.app.services.audio.stt.faster_whisper_streaming_speech_to_text_service import (
        FasterWhisperStreamingConfig,
        FasterWhisperStreamingSpeechToTextService,
    )

    return FasterWhisperStreamingSpeechToTextService(
        config=FasterWhisperStreamingConfig(
            model_id=model_id,
            model_path=Path(model_path).resolve() if model_path else None,
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
            vad_filter=vad_filter,
            vad_min_silence_duration_ms=vad_min_silence_duration_ms,
            vad_speech_pad_ms=vad_speech_pad_ms,
            no_speech_threshold=no_speech_threshold,
            condition_on_previous_text=condition_on_previous_text,
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
    )


def build_sherpa_onnx_streaming(
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
    """Sherpa ONNX 스트리밍 서비스를 생성한다."""

    from server.app.services.audio.stt.sherpa_onnx_streaming_speech_to_text_service import (
        SherpaOnnxStreamingConfig,
        SherpaOnnxStreamingSpeechToTextService,
    )

    resolved_model_path = Path(model_path).resolve() if model_path else Path(model_id).resolve()
    provider = "cuda" if device.startswith("cuda") else "cpu"
    decoding_method = "modified_beam_search" if beam_size > 1 else "greedy_search"
    return SherpaOnnxStreamingSpeechToTextService(
        config=SherpaOnnxStreamingConfig(
            model_path=resolved_model_path,
            language=language,
            provider=provider,
            num_threads=cpu_threads if cpu_threads > 0 else 2,
            sample_rate_hz=sample_rate_hz,
            sample_width_bytes=sample_width_bytes,
            channels=channels,
            decoding_method=decoding_method,
            max_active_paths=max(beam_size, 4),
            partial_emit_interval_ms=partial_emit_interval_ms,
            partial_agreement_window=partial_agreement_window,
            partial_agreement_min_count=partial_agreement_min_count,
            partial_min_stable_chars=partial_min_stable_chars,
            partial_min_growth_chars=partial_min_growth_chars,
            partial_backtrack_tolerance_chars=partial_backtrack_tolerance_chars,
            partial_commit_min_chars_without_boundary=partial_commit_min_chars_without_boundary,
        )
    )


def build_moonshine_streaming(
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
    """Moonshine 스트리밍 서비스를 생성한다."""

    from server.app.services.audio.stt.moonshine_streaming_speech_to_text_service import (
        MoonshineStreamingConfig,
        MoonshineStreamingSpeechToTextService,
    )

    return MoonshineStreamingSpeechToTextService(
        config=MoonshineStreamingConfig(
            model_id=model_id,
            model_path=Path(model_path).resolve() if model_path else None,
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
    )
