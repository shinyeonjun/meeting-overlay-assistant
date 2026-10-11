"""STT 팩토리 옵션 모델."""

from __future__ import annotations

from dataclasses import dataclass


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
