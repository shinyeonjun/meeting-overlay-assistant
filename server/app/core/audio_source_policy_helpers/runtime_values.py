"""Audio source policy의 preview/final/content gate 값 계산 helper."""

from __future__ import annotations


def build_runtime_values(*, profile_data: dict[str, object], settings, is_system_audio: bool) -> dict[str, object]:
    """Preview/final/runtime 관련 정책 값을 계산한다."""

    return {
        "preview_min_compact_length": int(
            profile_data.get("preview_min_compact_length", 1 if not is_system_audio else 2)
        ),
        "preview_backpressure_queue_delay_ms": int(
            profile_data.get("preview_backpressure_queue_delay_ms", 0 if not is_system_audio else 1800)
        ),
        "preview_backpressure_hold_chunks": int(
            profile_data.get("preview_backpressure_hold_chunks", 0 if not is_system_audio else 2)
        ),
        "segment_grace_match_max_gap_ms": int(
            profile_data.get("segment_grace_match_max_gap_ms", 0 if not is_system_audio else 1200)
        ),
        "live_final_emit_max_delay_ms": int(
            profile_data.get("live_final_emit_max_delay_ms", 0 if not is_system_audio else 3500)
        ),
        "live_final_initial_grace_segments": int(
            profile_data.get("live_final_initial_grace_segments", 0 if not is_system_audio else 3)
        ),
        "live_final_initial_grace_delay_ms": int(
            profile_data.get("live_final_initial_grace_delay_ms", 0 if not is_system_audio else 6000)
        ),
        "final_short_text_max_compact_length": int(
            profile_data.get("final_short_text_max_compact_length", 0 if not is_system_audio else 5)
        ),
        "final_short_text_min_confidence": float(
            profile_data.get(
                "final_short_text_min_confidence",
                settings.stt_short_text_min_confidence_system_audio
                if is_system_audio
                else settings.stt_short_text_min_confidence,
            )
        ),
        "duplicate_window_ms": int(
            profile_data.get(
                "duplicate_window_ms",
                settings.stt_duplicate_window_ms_system_audio
                if is_system_audio
                else settings.stt_duplicate_window_ms,
            )
        ),
        "duplicate_similarity_threshold": float(
            profile_data.get(
                "duplicate_similarity_threshold",
                settings.stt_duplicate_similarity_threshold_system_audio
                if is_system_audio
                else settings.stt_duplicate_similarity_threshold,
            )
        ),
        "duplicate_max_confidence": float(
            profile_data.get(
                "duplicate_max_confidence",
                settings.stt_duplicate_max_confidence_system_audio
                if is_system_audio
                else settings.stt_duplicate_max_confidence,
            )
        ),
        "content_gate_enabled": bool(profile_data["content_gate_enabled"]),
        "content_gate_min_rms": float(profile_data["content_gate_min_rms"]),
        "content_gate_min_speech_band_ratio": float(profile_data["content_gate_min_speech_band_ratio"]),
        "content_gate_min_spectral_flatness": float(profile_data["content_gate_min_spectral_flatness"]),
        "content_gate_min_zero_crossing_rate": float(profile_data["content_gate_min_zero_crossing_rate"]),
    }
