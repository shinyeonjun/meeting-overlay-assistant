"""STT 서비스 생성 팩토리."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from server.app.services.audio.stt.transcription import SpeechToTextService


@dataclass(frozen=True)
class SpeechToTextBuildOptions:
    """STT 서비스 생성 옵션."""

    backend_name: str
    model_id: str = "amd/whisper-small-onnx-npu"
    model_path: str | None = None
    base_model_id: str | None = None
    installation_path: str | None = None
    encoder_model_path: str | None = None
    decoder_model_path: str | None = None
    encoder_rai_path: str | None = None
    base_url: str = "http://127.0.0.1:8001/v1/audio"
    api_key: str | None = None
    timeout_seconds: float = 20.0
    language: str | None = "ko"
    initial_prompt: str | None = None
    device: str = "auto"
    compute_type: str = "default"
    cpu_threads: int = 0
    beam_size: int = 1
    sample_rate_hz: int = 16000
    sample_width_bytes: int = 2
    channels: int = 1
    silence_rms_threshold: float = 0.003
    partial_buffer_ms: int = 900
    partial_emit_interval_ms: int = 240
    partial_min_rms_threshold: float = 0.004
    partial_agreement_window: int = 2
    partial_agreement_min_count: int = 2
    partial_min_stable_chars: int = 4
    partial_min_growth_chars: int = 2
    partial_backtrack_tolerance_chars: int = 2
    partial_commit_min_chars_without_boundary: int = 6
    partial_backend_name: str | None = None
    partial_model_id: str | None = None
    partial_model_path: str | None = None
    partial_device: str | None = None
    partial_compute_type: str | None = None
    partial_cpu_threads: int | None = None
    partial_beam_size: int | None = None
    final_backend_name: str | None = None
    final_model_id: str | None = None
    final_model_path: str | None = None
    final_device: str | None = None
    final_compute_type: str | None = None
    final_cpu_threads: int | None = None
    final_beam_size: int | None = None


def create_speech_to_text_service(
    backend_name: str,
    model_id: str = "amd/whisper-small-onnx-npu",
    model_path: str | None = None,
    base_model_id: str | None = None,
    installation_path: str | None = None,
    encoder_model_path: str | None = None,
    decoder_model_path: str | None = None,
    encoder_rai_path: str | None = None,
    base_url: str = "http://127.0.0.1:8001/v1/audio",
    api_key: str | None = None,
    timeout_seconds: float = 20.0,
    language: str | None = "ko",
    initial_prompt: str | None = None,
    device: str = "auto",
    compute_type: str = "default",
    cpu_threads: int = 0,
    beam_size: int = 1,
    sample_rate_hz: int = 16000,
    sample_width_bytes: int = 2,
    channels: int = 1,
    silence_rms_threshold: float = 0.003,
    partial_buffer_ms: int = 900,
    partial_emit_interval_ms: int = 240,
    partial_min_rms_threshold: float = 0.004,
    partial_agreement_window: int = 2,
    partial_agreement_min_count: int = 2,
    partial_min_stable_chars: int = 4,
    partial_min_growth_chars: int = 2,
    partial_backtrack_tolerance_chars: int = 2,
    partial_commit_min_chars_without_boundary: int = 6,
    partial_backend_name: str | None = None,
    partial_model_id: str | None = None,
    partial_model_path: str | None = None,
    partial_device: str | None = None,
    partial_compute_type: str | None = None,
    partial_cpu_threads: int | None = None,
    partial_beam_size: int | None = None,
    final_backend_name: str | None = None,
    final_model_id: str | None = None,
    final_model_path: str | None = None,
    final_device: str | None = None,
    final_compute_type: str | None = None,
    final_cpu_threads: int | None = None,
    final_beam_size: int | None = None,
) -> SpeechToTextService:
    """설정값에 맞는 STT 서비스를 반환한다."""

    options = SpeechToTextBuildOptions(
        backend_name=backend_name,
        model_id=model_id,
        model_path=model_path,
        base_model_id=base_model_id,
        installation_path=installation_path,
        encoder_model_path=encoder_model_path,
        decoder_model_path=decoder_model_path,
        encoder_rai_path=encoder_rai_path,
        base_url=base_url,
        api_key=api_key,
        timeout_seconds=timeout_seconds,
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
        partial_backend_name=partial_backend_name,
        partial_model_id=partial_model_id,
        partial_model_path=partial_model_path,
        partial_device=partial_device,
        partial_compute_type=partial_compute_type,
        partial_cpu_threads=partial_cpu_threads,
        partial_beam_size=partial_beam_size,
        final_backend_name=final_backend_name,
        final_model_id=final_model_id,
        final_model_path=final_model_path,
        final_device=final_device,
        final_compute_type=final_compute_type,
        final_cpu_threads=final_cpu_threads,
        final_beam_size=final_beam_size,
    )
    return create_speech_to_text_service_from_options(options)


def create_speech_to_text_service_from_options(options: SpeechToTextBuildOptions) -> SpeechToTextService:
    """옵션 객체 기반으로 STT 서비스를 생성한다."""

    builders: dict[str, Callable[[], SpeechToTextService]] = {
        "placeholder": _build_placeholder,
        "openai_compatible_audio": lambda: _build_openai_compatible_audio(
            model_id=options.model_id,
            base_url=options.base_url,
            api_key=options.api_key,
            timeout_seconds=options.timeout_seconds,
            language=options.language,
            sample_rate_hz=options.sample_rate_hz,
            sample_width_bytes=options.sample_width_bytes,
            channels=options.channels,
        ),
        "amd_whisper_npu": lambda: _build_amd_whisper_npu(
            model_id=options.model_id,
            model_path=options.model_path,
            base_model_id=options.base_model_id,
            installation_path=options.installation_path,
            encoder_model_path=options.encoder_model_path,
            decoder_model_path=options.decoder_model_path,
            encoder_rai_path=options.encoder_rai_path,
            language=options.language,
            sample_rate_hz=options.sample_rate_hz,
            sample_width_bytes=options.sample_width_bytes,
            channels=options.channels,
            silence_rms_threshold=options.silence_rms_threshold,
        ),
        "faster_whisper": lambda: _build_faster_whisper(
            model_id=options.model_id,
            model_path=options.model_path,
            language=options.language,
            initial_prompt=options.initial_prompt,
            device=options.device,
            compute_type=options.compute_type,
            cpu_threads=options.cpu_threads,
            beam_size=options.beam_size,
            sample_rate_hz=options.sample_rate_hz,
            sample_width_bytes=options.sample_width_bytes,
            channels=options.channels,
            silence_rms_threshold=options.silence_rms_threshold,
        ),
        "faster_whisper_streaming": lambda: _build_faster_whisper_streaming(
            model_id=options.model_id,
            model_path=options.model_path,
            language=options.language,
            initial_prompt=options.initial_prompt,
            device=options.device,
            compute_type=options.compute_type,
            cpu_threads=options.cpu_threads,
            beam_size=options.beam_size,
            sample_rate_hz=options.sample_rate_hz,
            sample_width_bytes=options.sample_width_bytes,
            channels=options.channels,
            silence_rms_threshold=options.silence_rms_threshold,
            partial_buffer_ms=options.partial_buffer_ms,
            partial_emit_interval_ms=options.partial_emit_interval_ms,
            partial_min_rms_threshold=options.partial_min_rms_threshold,
            partial_agreement_window=options.partial_agreement_window,
            partial_agreement_min_count=options.partial_agreement_min_count,
            partial_min_stable_chars=options.partial_min_stable_chars,
            partial_min_growth_chars=options.partial_min_growth_chars,
            partial_backtrack_tolerance_chars=options.partial_backtrack_tolerance_chars,
            partial_commit_min_chars_without_boundary=options.partial_commit_min_chars_without_boundary,
        ),
        "sherpa_onnx_streaming": lambda: _build_sherpa_onnx_streaming(
            model_id=options.model_id,
            model_path=options.model_path,
            language=options.language,
            device=options.device,
            cpu_threads=options.cpu_threads,
            beam_size=options.beam_size,
            sample_rate_hz=options.sample_rate_hz,
            sample_width_bytes=options.sample_width_bytes,
            channels=options.channels,
            partial_emit_interval_ms=options.partial_emit_interval_ms,
            partial_agreement_window=options.partial_agreement_window,
            partial_agreement_min_count=options.partial_agreement_min_count,
            partial_min_stable_chars=options.partial_min_stable_chars,
            partial_min_growth_chars=options.partial_min_growth_chars,
            partial_backtrack_tolerance_chars=options.partial_backtrack_tolerance_chars,
            partial_commit_min_chars_without_boundary=options.partial_commit_min_chars_without_boundary,
        ),
        "hybrid_local_streaming": lambda: _build_hybrid_local_streaming(
            model_id=options.model_id,
            model_path=options.model_path,
            language=options.language,
            device=options.device,
            compute_type=options.compute_type,
            cpu_threads=options.cpu_threads,
            beam_size=options.beam_size,
            sample_rate_hz=options.sample_rate_hz,
            sample_width_bytes=options.sample_width_bytes,
            channels=options.channels,
            silence_rms_threshold=options.silence_rms_threshold,
            partial_buffer_ms=options.partial_buffer_ms,
            partial_emit_interval_ms=options.partial_emit_interval_ms,
            partial_min_rms_threshold=options.partial_min_rms_threshold,
            partial_agreement_window=options.partial_agreement_window,
            partial_agreement_min_count=options.partial_agreement_min_count,
            partial_min_stable_chars=options.partial_min_stable_chars,
            partial_min_growth_chars=options.partial_min_growth_chars,
            partial_backtrack_tolerance_chars=options.partial_backtrack_tolerance_chars,
            partial_commit_min_chars_without_boundary=options.partial_commit_min_chars_without_boundary,
            partial_backend_name=options.partial_backend_name,
            partial_model_id=options.partial_model_id,
            partial_model_path=options.partial_model_path,
            partial_device=options.partial_device,
            partial_compute_type=options.partial_compute_type,
            partial_cpu_threads=options.partial_cpu_threads,
            partial_beam_size=options.partial_beam_size,
            final_backend_name=options.final_backend_name,
            final_model_id=options.final_model_id,
            final_model_path=options.final_model_path,
            final_device=options.final_device,
            final_compute_type=options.final_compute_type,
            final_cpu_threads=options.final_cpu_threads,
            final_beam_size=options.final_beam_size,
        ),
        "moonshine": lambda: _build_moonshine(
            model_id=options.model_id,
            model_path=options.model_path,
            language=options.language,
            sample_rate_hz=options.sample_rate_hz,
            sample_width_bytes=options.sample_width_bytes,
            channels=options.channels,
            silence_rms_threshold=options.silence_rms_threshold,
        ),
        "moonshine_streaming": lambda: _build_moonshine_streaming(
            model_id=options.model_id,
            model_path=options.model_path,
            language=options.language,
            sample_rate_hz=options.sample_rate_hz,
            sample_width_bytes=options.sample_width_bytes,
            channels=options.channels,
            silence_rms_threshold=options.silence_rms_threshold,
            partial_buffer_ms=options.partial_buffer_ms,
            partial_emit_interval_ms=options.partial_emit_interval_ms,
            partial_min_rms_threshold=options.partial_min_rms_threshold,
            partial_agreement_window=options.partial_agreement_window,
            partial_agreement_min_count=options.partial_agreement_min_count,
            partial_min_stable_chars=options.partial_min_stable_chars,
            partial_min_growth_chars=options.partial_min_growth_chars,
        ),
    }
    if options.backend_name not in builders:
        raise ValueError(f"지원하지 않는 stt backend입니다: {options.backend_name}")
    return builders[options.backend_name]()


def _build_placeholder() -> SpeechToTextService:
    from server.app.services.audio.stt.placeholder_speech_to_text_service import (
        PlaceholderSpeechToTextService,
    )

    return PlaceholderSpeechToTextService()


def _build_openai_compatible_audio(
    *,
    model_id: str,
    base_url: str,
    api_key: str | None,
    timeout_seconds: float,
    language: str | None,
    sample_rate_hz: int,
    sample_width_bytes: int,
    channels: int,
) -> SpeechToTextService:
    from server.app.services.audio.stt.openai_compatible_audio_transcription_service import (
        OpenAICompatibleAudioTranscriptionService,
    )

    return OpenAICompatibleAudioTranscriptionService(
        model=model_id,
        base_url=base_url,
        api_key=api_key,
        timeout_seconds=timeout_seconds,
        language=language,
        sample_rate_hz=sample_rate_hz,
        sample_width_bytes=sample_width_bytes,
        channels=channels,
    )


def _build_amd_whisper_npu(
    *,
    model_id: str,
    model_path: str | None,
    base_model_id: str | None,
    installation_path: str | None,
    encoder_model_path: str | None,
    decoder_model_path: str | None,
    encoder_rai_path: str | None,
    language: str | None,
    sample_rate_hz: int,
    sample_width_bytes: int,
    channels: int,
    silence_rms_threshold: float,
) -> SpeechToTextService:
    from server.app.services.audio.stt.amd_whisper_npu_speech_to_text_service import (
        AMDWhisperNPUConfig,
        AMDWhisperNPUSpeechToTextService,
    )

    return AMDWhisperNPUSpeechToTextService(
        config=AMDWhisperNPUConfig(
            model_id=model_id,
            model_path=Path(model_path).resolve() if model_path else None,
            base_model_id=base_model_id,
            installation_path=Path(installation_path).resolve() if installation_path else None,
            encoder_model_path=Path(encoder_model_path).resolve() if encoder_model_path else None,
            decoder_model_path=Path(decoder_model_path).resolve() if decoder_model_path else None,
            encoder_rai_path=Path(encoder_rai_path).resolve() if encoder_rai_path else None,
            language=language,
            sample_rate_hz=sample_rate_hz,
            sample_width_bytes=sample_width_bytes,
            channels=channels,
            silence_rms_threshold=silence_rms_threshold,
        )
    )


def _build_faster_whisper(
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
) -> SpeechToTextService:
    from server.app.services.audio.stt.faster_whisper_speech_to_text_service import (
        FasterWhisperConfig,
        FasterWhisperSpeechToTextService,
    )

    return FasterWhisperSpeechToTextService(
        config=FasterWhisperConfig(
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
        )
    )


def _build_faster_whisper_streaming(
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


def _build_hybrid_local_streaming(
    *,
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
    from server.app.services.audio.stt.hybrid_streaming_speech_to_text_service import (
        HybridStreamingConfig,
        HybridStreamingSpeechToTextService,
    )
    from server.app.services.audio.stt.transcription import StreamingSpeechToTextService

    resolved_partial_backend_name = partial_backend_name or "faster_whisper_streaming"
    resolved_final_backend_name = final_backend_name or "faster_whisper"

    if resolved_partial_backend_name == "hybrid_local_streaming":
        raise ValueError("hybrid_local_streaming의 partial backend로 자신을 다시 지정할 수 없습니다.")
    if resolved_final_backend_name == "hybrid_local_streaming":
        raise ValueError("hybrid_local_streaming의 final backend로 자신을 다시 지정할 수 없습니다.")

    partial_service = create_speech_to_text_service(
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

    final_service = create_speech_to_text_service(
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

    return HybridStreamingSpeechToTextService(
        config=HybridStreamingConfig(reset_partial_stream_on_final=True),
        partial_service=partial_service,
        final_service=final_service,
    )


def _build_sherpa_onnx_streaming(
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


def _build_moonshine(
    *,
    model_id: str,
    model_path: str | None,
    language: str | None,
    sample_rate_hz: int,
    sample_width_bytes: int,
    channels: int,
    silence_rms_threshold: float,
) -> SpeechToTextService:
    from server.app.services.audio.stt.moonshine_speech_to_text_service import (
        MoonshineConfig,
        MoonshineSpeechToTextService,
    )

    return MoonshineSpeechToTextService(
        config=MoonshineConfig(
            model_id=model_id,
            model_path=Path(model_path).resolve() if model_path else None,
            language=language,
            sample_rate_hz=sample_rate_hz,
            sample_width_bytes=sample_width_bytes,
            channels=channels,
            silence_rms_threshold=silence_rms_threshold,
        )
    )


def _build_moonshine_streaming(
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

