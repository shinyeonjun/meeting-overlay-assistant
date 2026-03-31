"""Audio source policy의 guard 관련 값 계산 helper."""

from __future__ import annotations


def build_guard_values(*, profile_data: dict[str, object], settings, is_system_audio: bool) -> dict[str, object]:
    """Transcription guard 관련 정책 값을 계산한다."""

    return {
        "guard_min_confidence": float(
            profile_data.get(
                "guard_min_confidence",
                settings.stt_min_confidence_system_audio
                if is_system_audio
                else settings.stt_min_confidence,
            )
        ),
        "guard_short_text_min_confidence": float(
            profile_data.get(
                "guard_short_text_min_confidence",
                settings.stt_short_text_min_confidence_system_audio
                if is_system_audio
                else settings.stt_short_text_min_confidence,
            )
        ),
        "guard_max_repeat_ratio": float(
            profile_data.get(
                "guard_max_repeat_ratio",
                settings.stt_max_repeat_ratio_system_audio
                if is_system_audio
                else settings.stt_max_repeat_ratio,
            )
        ),
        "guard_max_consecutive_repeat": int(
            profile_data.get(
                "guard_max_consecutive_repeat",
                settings.stt_max_consecutive_repeat_system_audio
                if is_system_audio
                else settings.stt_max_consecutive_repeat,
            )
        ),
        "guard_min_repetition_tokens": int(
            profile_data.get(
                "guard_min_repetition_tokens",
                settings.stt_min_repetition_tokens_system_audio
                if is_system_audio
                else settings.stt_min_repetition_tokens,
            )
        ),
        "guard_blocked_phrases_enabled": bool(profile_data["guard_blocked_phrases_enabled"]),
        "guard_language_consistency_enabled": bool(profile_data["guard_language_consistency_enabled"]),
        "guard_language_consistency_max_confidence": float(
            profile_data.get(
                "guard_language_consistency_max_confidence",
                settings.stt_language_consistency_max_confidence_system_audio
                if is_system_audio
                else settings.stt_language_consistency_max_confidence,
            )
        ),
        "guard_min_target_script_ratio": float(
            profile_data.get(
                "guard_min_target_script_ratio",
                settings.stt_min_target_script_ratio_system_audio
                if is_system_audio
                else settings.stt_min_target_script_ratio,
            )
        ),
        "guard_min_letter_ratio": float(
            profile_data.get(
                "guard_min_letter_ratio",
                settings.stt_min_letter_ratio_system_audio
                if is_system_audio
                else settings.stt_min_letter_ratio,
            )
        ),
        "guard_max_no_speech_prob": float(
            profile_data.get(
                "guard_max_no_speech_prob",
                settings.stt_max_no_speech_prob_system_audio
                if is_system_audio
                else settings.stt_max_no_speech_prob,
            )
        ),
    }
