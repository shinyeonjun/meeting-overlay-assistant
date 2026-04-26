"""AppConfig 오디오/실시간 섹션."""

from __future__ import annotations

from server.app.core.config_helpers.env import get_bool, get_env, get_float, get_int


def build_audio_values() -> dict[str, object]:
    """오디오 전처리, diarizer, STT, VAD, live streaming 설정을 조립한다."""

    return {
        "audio_preprocessor_backend": get_env("AUDIO_PREPROCESSOR_BACKEND", "bypass") or "bypass",
        "audio_preprocessor_model_path": get_env("AUDIO_PREPROCESSOR_MODEL_PATH"),
        "audio_preprocessor_atten_lim_db": get_int("AUDIO_PREPROCESSOR_ATTEN_LIM_DB", 18),
        "speaker_diarizer_backend": get_env("SPEAKER_DIARIZER_BACKEND", "unknown_speaker")
        or "unknown_speaker",
        "speaker_diarizer_model_id": get_env(
            "SPEAKER_DIARIZER_MODEL_ID",
            "pyannote/speaker-diarization-community-1",
        )
        or "pyannote/speaker-diarization-community-1",
        "speaker_diarizer_auth_token": get_env("SPEAKER_DIARIZER_AUTH_TOKEN"),
        "speaker_diarizer_device": get_env("SPEAKER_DIARIZER_DEVICE", "cpu") or "cpu",
        "speaker_diarizer_default_label": get_env("SPEAKER_DIARIZER_DEFAULT_LABEL", "speaker-unknown")
        or "speaker-unknown",
        "speaker_diarizer_worker_python": get_env("SPEAKER_DIARIZER_WORKER_PYTHON"),
        "speaker_diarizer_worker_script_path": get_env("SPEAKER_DIARIZER_WORKER_SCRIPT_PATH"),
        "speaker_diarizer_worker_timeout_seconds": get_int("SPEAKER_DIARIZER_WORKER_TIMEOUT_SECONDS", 120),
        "stt_backend": get_env("STT_BACKEND", "faster_whisper") or "faster_whisper",
        "stt_backend_system_audio": get_env("STT_BACKEND_SYSTEM_AUDIO"),
        "stt_model_id": get_env("STT_MODEL_ID", "deepdml/faster-whisper-large-v3-turbo-ct2")
        or "deepdml/faster-whisper-large-v3-turbo-ct2",
        "stt_model_path": get_env("STT_MODEL_PATH"),
        "stt_base_model_id": get_env("STT_BASE_MODEL_ID", "openai/whisper-small")
        or "openai/whisper-small",
        "stt_encoder_model_path": get_env("STT_ENCODER_MODEL_PATH"),
        "stt_decoder_model_path": get_env("STT_DECODER_MODEL_PATH"),
        "stt_encoder_rai_path": get_env("STT_ENCODER_RAI_PATH"),
        "stt_base_url": get_env("STT_BASE_URL"),
        "stt_api_key": get_env("STT_API_KEY"),
        "stt_timeout_seconds": get_int("STT_TIMEOUT_SECONDS", 20),
        "stt_preload_on_startup": get_bool("STT_PRELOAD_ON_STARTUP", True),
        "mic_server_stt_fallback_enabled": get_bool(
            "MIC_SERVER_STT_FALLBACK_ENABLED",
            False,
        ),
        "mic_server_stt_preload_enabled": get_bool(
            "MIC_SERVER_STT_PRELOAD_ENABLED",
            False,
        ),
        "stt_language": get_env("STT_LANGUAGE", "ko") or "ko",
        "stt_initial_prompt": get_env("STT_INITIAL_PROMPT"),
        "stt_device": get_env("STT_DEVICE", "auto") or "auto",
        "stt_compute_type": get_env("STT_COMPUTE_TYPE", "default") or "default",
        "stt_cpu_threads": get_int("STT_CPU_THREADS", 0),
        "stt_beam_size": get_int("STT_BEAM_SIZE", 1),
        "stt_sample_rate_hz": get_int("STT_SAMPLE_RATE_HZ", 16000),
        "stt_sample_width_bytes": get_int("STT_SAMPLE_WIDTH_BYTES", 2),
        "stt_channels": get_int("STT_CHANNELS", 1),
        "stt_silence_rms_threshold": get_float("STT_SILENCE_RMS_THRESHOLD", 0.003),
        "stt_min_confidence": get_float("STT_MIN_CONFIDENCE", 0.35),
        "stt_min_confidence_system_audio": get_float("STT_MIN_CONFIDENCE_SYSTEM_AUDIO", 0.6),
        "stt_short_text_min_confidence": get_float("STT_SHORT_TEXT_MIN_CONFIDENCE", 0.6),
        "stt_short_text_min_confidence_system_audio": get_float(
            "STT_SHORT_TEXT_MIN_CONFIDENCE_SYSTEM_AUDIO",
            0.8,
        ),
        "stt_min_compact_length": get_int("STT_MIN_COMPACT_LENGTH", 2),
        "stt_max_repeat_ratio": get_float("STT_MAX_REPEAT_RATIO", 0.6),
        "stt_max_repeat_ratio_system_audio": get_float("STT_MAX_REPEAT_RATIO_SYSTEM_AUDIO", 0.5),
        "stt_max_consecutive_repeat": get_int("STT_MAX_CONSECUTIVE_REPEAT", 4),
        "stt_max_consecutive_repeat_system_audio": get_int("STT_MAX_CONSECUTIVE_REPEAT_SYSTEM_AUDIO", 3),
        "stt_min_repetition_tokens": get_int("STT_MIN_REPETITION_TOKENS", 6),
        "stt_min_repetition_tokens_system_audio": get_int("STT_MIN_REPETITION_TOKENS_SYSTEM_AUDIO", 4),
        "stt_language_consistency_max_confidence": get_float(
            "STT_LANGUAGE_CONSISTENCY_MAX_CONFIDENCE",
            0.7,
        ),
        "stt_language_consistency_max_confidence_system_audio": get_float(
            "STT_LANGUAGE_CONSISTENCY_MAX_CONFIDENCE_SYSTEM_AUDIO",
            0.75,
        ),
        "stt_min_target_script_ratio": get_float("STT_MIN_TARGET_SCRIPT_RATIO", 0.35),
        "stt_min_target_script_ratio_system_audio": get_float(
            "STT_MIN_TARGET_SCRIPT_RATIO_SYSTEM_AUDIO",
            0.45,
        ),
        "stt_min_letter_ratio": get_float("STT_MIN_LETTER_RATIO", 0.45),
        "stt_min_letter_ratio_system_audio": get_float("STT_MIN_LETTER_RATIO_SYSTEM_AUDIO", 0.55),
        "stt_duplicate_window_ms": get_int("STT_DUPLICATE_WINDOW_MS", 2500),
        "stt_duplicate_window_ms_system_audio": get_int("STT_DUPLICATE_WINDOW_MS_SYSTEM_AUDIO", 8000),
        "stt_duplicate_similarity_threshold": get_float("STT_DUPLICATE_SIMILARITY_THRESHOLD", 0.98),
        "stt_duplicate_similarity_threshold_system_audio": get_float(
            "STT_DUPLICATE_SIMILARITY_THRESHOLD_SYSTEM_AUDIO",
            0.9,
        ),
        "stt_duplicate_max_confidence": get_float("STT_DUPLICATE_MAX_CONFIDENCE", 0.0),
        "stt_duplicate_max_confidence_system_audio": get_float(
            "STT_DUPLICATE_MAX_CONFIDENCE_SYSTEM_AUDIO",
            0.8,
        ),
        "stt_max_no_speech_prob": get_float("STT_MAX_NO_SPEECH_PROB", 1.0),
        "stt_max_no_speech_prob_system_audio": get_float(
            "STT_MAX_NO_SPEECH_PROB_SYSTEM_AUDIO",
            0.8,
        ),
        "vad_frame_duration_ms": get_int("VAD_FRAME_DURATION_MS", 30),
        "vad_pre_roll_ms": get_int("VAD_PRE_ROLL_MS", 300),
        "vad_post_roll_ms": get_int("VAD_POST_ROLL_MS", 450),
        "vad_post_roll_ms_system_audio": get_int("VAD_POST_ROLL_MS_SYSTEM_AUDIO", 650),
        "vad_min_speech_ms": get_int("VAD_MIN_SPEECH_MS", 240),
        "vad_min_speech_ms_system_audio": get_int("VAD_MIN_SPEECH_MS_SYSTEM_AUDIO", 180),
        "vad_max_segment_ms": get_int("VAD_MAX_SEGMENT_MS", 5000),
        "vad_min_activation_frames": get_int("VAD_MIN_ACTIVATION_FRAMES", 2),
        "vad_min_activation_frames_system_audio": get_int("VAD_MIN_ACTIVATION_FRAMES_SYSTEM_AUDIO", 2),
        "vad_rms_threshold": get_float("VAD_RMS_THRESHOLD", 0.01),
        "vad_rms_threshold_system_audio": get_float("VAD_RMS_THRESHOLD_SYSTEM_AUDIO", 0.008),
        "vad_adaptive_noise_floor_alpha": get_float("VAD_ADAPTIVE_NOISE_FLOOR_ALPHA", 0.92),
        "vad_adaptive_threshold_multiplier": get_float("VAD_ADAPTIVE_THRESHOLD_MULTIPLIER", 1.9),
        "vad_adaptive_threshold_multiplier_system_audio": get_float(
            "VAD_ADAPTIVE_THRESHOLD_MULTIPLIER_SYSTEM_AUDIO",
            1.55,
        ),
        "vad_active_threshold_ratio": get_float("VAD_ACTIVE_THRESHOLD_RATIO", 0.8),
        "vad_active_threshold_ratio_system_audio": get_float("VAD_ACTIVE_THRESHOLD_RATIO_SYSTEM_AUDIO", 0.72),
        "vad_min_voiced_ratio": get_float("VAD_MIN_VOICED_RATIO", 0.18),
        "vad_min_voiced_ratio_system_audio": get_float("VAD_MIN_VOICED_RATIO_SYSTEM_AUDIO", 0.12),
        "silero_vad_enabled": get_bool("SILERO_VAD_ENABLED", False),
        "silero_vad_enabled_system_audio": get_bool("SILERO_VAD_ENABLED_SYSTEM_AUDIO", False),
        "silero_vad_threshold": get_float("SILERO_VAD_THRESHOLD", 0.5),
        "silero_vad_min_speech_ms": get_int("SILERO_VAD_MIN_SPEECH_MS", 120),
        "ryzen_ai_installation_path": get_env("RYZEN_AI_INSTALLATION_PATH"),
        "partial_buffer_ms": get_int("PARTIAL_BUFFER_MS", 900),
        "partial_emit_interval_ms": get_int("PARTIAL_EMIT_INTERVAL_MS", 240),
        "partial_min_rms_threshold": get_float("PARTIAL_MIN_RMS_THRESHOLD", 0.006),
        "partial_agreement_window": get_int("PARTIAL_AGREEMENT_WINDOW", 3),
        "partial_agreement_min_count": get_int("PARTIAL_AGREEMENT_MIN_COUNT", 2),
        "partial_min_stable_chars": get_int("PARTIAL_MIN_STABLE_CHARS", 2),
        "partial_min_growth_chars": get_int("PARTIAL_MIN_GROWTH_CHARS", 2),
        "partial_backtrack_tolerance_chars": get_int("PARTIAL_BACKTRACK_TOLERANCE_CHARS", 2),
        "partial_commit_min_chars_without_boundary": get_int(
            "PARTIAL_COMMIT_MIN_CHARS_WITHOUT_BOUNDARY",
            6,
        ),
        "live_stream_worker_count": get_int("LIVE_STREAM_WORKER_COUNT", 1),
        "live_stream_pending_chunks_per_stream": get_int("LIVE_STREAM_PENDING_CHUNKS_PER_STREAM", 3),
        "live_stream_max_running_sessions": get_int("LIVE_STREAM_MAX_RUNNING_SESSIONS", 4),
        "live_stream_max_running_mic_streams": get_int(
            "LIVE_STREAM_MAX_RUNNING_MIC_STREAMS",
            1,
        ),
        "live_stream_max_running_system_audio_streams": get_int(
            "LIVE_STREAM_MAX_RUNNING_SYSTEM_AUDIO_STREAMS",
            2,
        ),
    }
