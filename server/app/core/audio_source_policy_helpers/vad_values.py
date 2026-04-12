"""Audio source policy의 VAD 관련 값 계산 helper."""

from __future__ import annotations


def build_vad_values(*, profile_data: dict[str, object], settings, is_system_audio: bool) -> dict[str, object]:
    """VAD 관련 정책 값을 계산한다."""

    return {
        "use_vad": bool(profile_data["use_vad"]),
        "vad_early_post_roll_ms": int(
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
        "vad_post_roll_ms": int(
            profile_data.get(
                "vad_post_roll_ms",
                settings.vad_post_roll_ms_system_audio
                if is_system_audio
                else settings.vad_post_roll_ms,
            )
        ),
        "vad_min_speech_ms": int(
            profile_data.get(
                "vad_min_speech_ms",
                settings.vad_min_speech_ms_system_audio
                if is_system_audio
                else settings.vad_min_speech_ms,
            )
        ),
        "vad_max_segment_ms": int(
            profile_data.get(
                "vad_max_segment_ms",
                settings.vad_max_segment_ms,
            )
        ),
        "vad_min_activation_frames": int(
            profile_data.get(
                "vad_min_activation_frames",
                settings.vad_min_activation_frames_system_audio
                if is_system_audio
                else settings.vad_min_activation_frames,
            )
        ),
        "vad_rms_threshold": float(
            profile_data.get(
                "vad_rms_threshold",
                settings.vad_rms_threshold_system_audio
                if is_system_audio
                else settings.vad_rms_threshold,
            )
        ),
        "vad_adaptive_threshold_multiplier": float(
            profile_data.get(
                "vad_adaptive_threshold_multiplier",
                settings.vad_adaptive_threshold_multiplier_system_audio
                if is_system_audio
                else settings.vad_adaptive_threshold_multiplier,
            )
        ),
        "vad_active_threshold_ratio": float(
            profile_data.get(
                "vad_active_threshold_ratio",
                settings.vad_active_threshold_ratio_system_audio
                if is_system_audio
                else settings.vad_active_threshold_ratio,
            )
        ),
        "vad_min_voiced_ratio": float(
            profile_data.get(
                "vad_min_voiced_ratio",
                settings.vad_min_voiced_ratio_system_audio
                if is_system_audio
                else settings.vad_min_voiced_ratio,
            )
        ),
        "silero_vad_enabled": bool(
            profile_data.get(
                "silero_vad_enabled",
                settings.silero_vad_enabled_system_audio
                if is_system_audio
                else settings.silero_vad_enabled,
            )
        ),
    }
