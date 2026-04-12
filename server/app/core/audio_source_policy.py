"""입력 소스별 오디오 처리 정책."""

from __future__ import annotations

from dataclasses import dataclass

from server.app.core.audio_source_policy_helpers import (
    build_audio_source_policy_kwargs,
    load_audio_source_profiles,
)
from server.app.core.config import AppConfig


@dataclass(frozen=True)
class AudioSourcePolicy:
    """입력 소스별 오디오 처리 정책 묶음."""

    source: str
    use_vad: bool
    vad_early_post_roll_ms: int
    vad_post_roll_ms: int
    vad_min_speech_ms: int
    vad_max_segment_ms: int
    vad_min_activation_frames: int
    vad_rms_threshold: float
    vad_adaptive_threshold_multiplier: float
    vad_active_threshold_ratio: float
    vad_min_voiced_ratio: float
    guard_min_confidence: float
    guard_short_text_min_confidence: float
    guard_max_repeat_ratio: float
    guard_max_consecutive_repeat: int
    guard_min_repetition_tokens: int
    guard_blocked_phrases_enabled: bool
    guard_language_consistency_enabled: bool
    guard_language_consistency_max_confidence: float
    guard_min_target_script_ratio: float
    guard_min_letter_ratio: float
    guard_max_no_speech_prob: float
    preview_min_compact_length: int
    preview_backpressure_queue_delay_ms: int
    preview_backpressure_hold_chunks: int
    segment_grace_match_max_gap_ms: int
    live_final_emit_max_delay_ms: int
    live_final_initial_grace_segments: int
    live_final_initial_grace_delay_ms: int
    final_short_text_max_compact_length: int
    final_short_text_min_confidence: float
    duplicate_window_ms: int
    duplicate_similarity_threshold: float
    duplicate_max_confidence: float
    content_gate_enabled: bool
    content_gate_min_rms: float
    content_gate_min_speech_band_ratio: float
    content_gate_min_spectral_flatness: float
    content_gate_min_zero_crossing_rate: float
    silero_vad_enabled: bool


def resolve_audio_source_policy(source: str, settings: AppConfig) -> AudioSourcePolicy:
    """입력 소스에 맞는 정책을 계산한다."""

    profiles = load_audio_source_profiles(str(settings.audio_source_profiles_config_path))
    return AudioSourcePolicy(
        **build_audio_source_policy_kwargs(
            source=source,
            settings=settings,
            profiles=profiles,
        )
    )
