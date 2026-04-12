"""입력 소스별 오디오 처리 정책."""

from __future__ import annotations

import json
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

from backend.app.core.config import AppConfig
from backend.app.domain.shared.enums import AudioSource


@dataclass(frozen=True)
class AudioSourcePolicy:
    """입력 소스에 따라 달라지는 오디오 처리 정책 묶음."""

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


@lru_cache(maxsize=8)
def _load_audio_source_profiles(path: str) -> dict[str, dict[str, object]]:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def resolve_audio_source_policy(source: str, settings: AppConfig) -> AudioSourcePolicy:
    """입력 소스에 맞는 정책을 계산한다."""
    is_system_audio = source in (AudioSource.SYSTEM_AUDIO.value, AudioSource.MIC_AND_AUDIO.value)
    profiles = _load_audio_source_profiles(str(settings.audio_source_profiles_config_path))
    profile_data = {
        **profiles.get("default", {}),
        **profiles.get(source, {}),
    }
    use_vad_default = source in (
        AudioSource.MIC.value,
        AudioSource.SYSTEM_AUDIO.value,
        AudioSource.MIC_AND_AUDIO.value,
    )

    return AudioSourcePolicy(
        source=source,
        use_vad=bool(profile_data.get("use_vad", use_vad_default)),
        vad_early_post_roll_ms=int(
            profile_data.get(
                "vad_early_post_roll_ms",
                profile_data.get(
                    "vad_post_roll_ms",
                    settings.vad_post_roll_ms_system_audio
                    if is_system_audio
                    else settings.vad_post_roll_ms,
                ),
            )
        ),
        vad_post_roll_ms=int(
            profile_data.get(
                "vad_post_roll_ms",
                settings.vad_post_roll_ms_system_audio
                if is_system_audio
                else settings.vad_post_roll_ms,
            )
        ),
        vad_min_speech_ms=int(
            profile_data.get(
                "vad_min_speech_ms",
                settings.vad_min_speech_ms_system_audio
                if is_system_audio
                else settings.vad_min_speech_ms,
            )
        ),
        vad_max_segment_ms=int(
            profile_data.get(
                "vad_max_segment_ms",
                settings.vad_max_segment_ms,
            )
        ),
        vad_min_activation_frames=int(
            profile_data.get(
                "vad_min_activation_frames",
                settings.vad_min_activation_frames_system_audio
                if is_system_audio
                else settings.vad_min_activation_frames,
            )
        ),
        vad_rms_threshold=float(
            profile_data.get(
                "vad_rms_threshold",
                settings.vad_rms_threshold_system_audio
                if is_system_audio
                else settings.vad_rms_threshold,
            )
        ),
        vad_adaptive_threshold_multiplier=float(
            profile_data.get(
                "vad_adaptive_threshold_multiplier",
                settings.vad_adaptive_threshold_multiplier_system_audio
                if is_system_audio
                else settings.vad_adaptive_threshold_multiplier,
            )
        ),
        vad_active_threshold_ratio=float(
            profile_data.get(
                "vad_active_threshold_ratio",
                settings.vad_active_threshold_ratio_system_audio
                if is_system_audio
                else settings.vad_active_threshold_ratio,
            )
        ),
        vad_min_voiced_ratio=float(
            profile_data.get(
                "vad_min_voiced_ratio",
                settings.vad_min_voiced_ratio_system_audio
                if is_system_audio
                else settings.vad_min_voiced_ratio,
            )
        ),
        guard_min_confidence=float(
            profile_data.get(
                "guard_min_confidence",
                settings.stt_min_confidence_system_audio
                if is_system_audio
                else settings.stt_min_confidence,
            )
        ),
        guard_short_text_min_confidence=float(
            profile_data.get(
                "guard_short_text_min_confidence",
                settings.stt_short_text_min_confidence_system_audio
                if is_system_audio
                else settings.stt_short_text_min_confidence,
            )
        ),
        guard_max_repeat_ratio=float(
            profile_data.get(
                "guard_max_repeat_ratio",
                settings.stt_max_repeat_ratio_system_audio
                if is_system_audio
                else settings.stt_max_repeat_ratio,
            )
        ),
        guard_max_consecutive_repeat=int(
            profile_data.get(
                "guard_max_consecutive_repeat",
                settings.stt_max_consecutive_repeat_system_audio
                if is_system_audio
                else settings.stt_max_consecutive_repeat,
            )
        ),
        guard_min_repetition_tokens=int(
            profile_data.get(
                "guard_min_repetition_tokens",
                settings.stt_min_repetition_tokens_system_audio
                if is_system_audio
                else settings.stt_min_repetition_tokens,
            )
        ),
        guard_blocked_phrases_enabled=bool(profile_data["guard_blocked_phrases_enabled"]),
        guard_language_consistency_enabled=bool(profile_data["guard_language_consistency_enabled"]),
        guard_language_consistency_max_confidence=float(
            profile_data.get(
                "guard_language_consistency_max_confidence",
                settings.stt_language_consistency_max_confidence_system_audio
                if is_system_audio
                else settings.stt_language_consistency_max_confidence,
            )
        ),
        guard_min_target_script_ratio=float(
            profile_data.get(
                "guard_min_target_script_ratio",
                settings.stt_min_target_script_ratio_system_audio
                if is_system_audio
                else settings.stt_min_target_script_ratio,
            )
        ),
        guard_min_letter_ratio=float(
            profile_data.get(
                "guard_min_letter_ratio",
                settings.stt_min_letter_ratio_system_audio
                if is_system_audio
                else settings.stt_min_letter_ratio,
            )
        ),
        guard_max_no_speech_prob=float(
            profile_data.get(
                "guard_max_no_speech_prob",
                settings.stt_max_no_speech_prob_system_audio
                if is_system_audio
                else settings.stt_max_no_speech_prob,
            )
        ),
        preview_min_compact_length=int(profile_data.get("preview_min_compact_length", 1 if not is_system_audio else 2)),
        final_short_text_max_compact_length=int(
            profile_data.get("final_short_text_max_compact_length", 0 if not is_system_audio else 5)
        ),
        preview_backpressure_queue_delay_ms=int(
            profile_data.get("preview_backpressure_queue_delay_ms", 0 if not is_system_audio else 1800)
        ),
        preview_backpressure_hold_chunks=int(
            profile_data.get("preview_backpressure_hold_chunks", 0 if not is_system_audio else 2)
        ),
        segment_grace_match_max_gap_ms=int(
            profile_data.get("segment_grace_match_max_gap_ms", 0 if not is_system_audio else 1200)
        ),
        live_final_emit_max_delay_ms=int(
            profile_data.get("live_final_emit_max_delay_ms", 0 if not is_system_audio else 3500)
        ),
        live_final_initial_grace_segments=int(
            profile_data.get("live_final_initial_grace_segments", 0 if not is_system_audio else 3)
        ),
        live_final_initial_grace_delay_ms=int(
            profile_data.get("live_final_initial_grace_delay_ms", 0 if not is_system_audio else 6000)
        ),
        final_short_text_min_confidence=float(
            profile_data.get(
                "final_short_text_min_confidence",
                settings.stt_short_text_min_confidence_system_audio
                if is_system_audio
                else settings.stt_short_text_min_confidence,
            )
        ),
        duplicate_window_ms=int(
            profile_data.get(
                "duplicate_window_ms",
                settings.stt_duplicate_window_ms_system_audio
                if is_system_audio
                else settings.stt_duplicate_window_ms,
            )
        ),
        duplicate_similarity_threshold=float(
            profile_data.get(
                "duplicate_similarity_threshold",
                settings.stt_duplicate_similarity_threshold_system_audio
                if is_system_audio
                else settings.stt_duplicate_similarity_threshold,
            )
        ),
        duplicate_max_confidence=float(
            profile_data.get(
                "duplicate_max_confidence",
                settings.stt_duplicate_max_confidence_system_audio
                if is_system_audio
                else settings.stt_duplicate_max_confidence,
            )
        ),
        content_gate_enabled=bool(profile_data["content_gate_enabled"]),
        content_gate_min_rms=float(profile_data["content_gate_min_rms"]),
        content_gate_min_speech_band_ratio=float(profile_data["content_gate_min_speech_band_ratio"]),
        content_gate_min_spectral_flatness=float(profile_data["content_gate_min_spectral_flatness"]),
        content_gate_min_zero_crossing_rate=float(profile_data["content_gate_min_zero_crossing_rate"]),
        silero_vad_enabled=bool(
            profile_data.get(
                "silero_vad_enabled",
                settings.silero_vad_enabled_system_audio
                if is_system_audio
                else settings.silero_vad_enabled,
            )
        ),
    )
