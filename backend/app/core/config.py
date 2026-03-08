from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

try:
    from dotenv import load_dotenv
except ImportError:  # pragma: no cover - 선택 의존성
    load_dotenv = None


ROOT_DIR = Path(__file__).resolve().parents[3]
ENV_PATH = ROOT_DIR / ".env"

if load_dotenv is not None and ENV_PATH.exists():
    load_dotenv(ENV_PATH)


def _get_env(name: str, default: str | None = None) -> str | None:
    value = os.getenv(name)
    if value is None or value == "":
        return default
    return value


def _get_bool(name: str, default: bool) -> bool:
    value = _get_env(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _get_int(name: str, default: int) -> int:
    value = _get_env(name)
    if value is None:
        return default
    return int(value)


def _get_float(name: str, default: float) -> float:
    value = _get_env(name)
    if value is None:
        return default
    return float(value)


def _get_csv(name: str, default: list[str]) -> list[str]:
    value = _get_env(name)
    if value is None:
        return default
    return [item.strip() for item in value.split(",") if item.strip()]


def _get_path(name: str, default: str) -> Path:
    raw = _get_env(name, default) or default
    path = Path(raw)
    if not path.is_absolute():
        path = ROOT_DIR / path
    return path


@dataclass(frozen=True)
class AppConfig:
    app_name: str
    app_env: str
    debug: bool
    database_path: Path
    log_level: str
    log_json: bool
    cors_allowed_origins: list[str]
    analysis_rules_config_path: Path
    transcription_guard_config_path: Path
    audio_source_profiles_config_path: Path
    ai_service_profiles_config_path: Path
    media_service_profiles_config_path: Path
    acceptance_profiles_config_path: Path
    audio_preprocessor_backend: str
    audio_preprocessor_model_path: str | None
    audio_preprocessor_atten_lim_db: int
    speaker_diarizer_backend: str
    speaker_diarizer_model_id: str
    speaker_diarizer_auth_token: str | None
    speaker_diarizer_device: str
    speaker_diarizer_default_label: str
    speaker_diarizer_worker_python: str | None
    speaker_diarizer_worker_script_path: str | None
    speaker_diarizer_worker_timeout_seconds: int
    stt_backend: str
    stt_backend_system_audio: str | None
    stt_model_id: str
    stt_model_path: str | None
    stt_base_model_id: str
    stt_encoder_model_path: str | None
    stt_decoder_model_path: str | None
    stt_encoder_rai_path: str | None
    stt_base_url: str | None
    stt_api_key: str | None
    stt_timeout_seconds: int
    stt_preload_on_startup: bool
    stt_language: str
    stt_initial_prompt: str | None
    stt_device: str
    stt_compute_type: str
    stt_cpu_threads: int
    stt_beam_size: int
    stt_sample_rate_hz: int
    stt_sample_width_bytes: int
    stt_channels: int
    stt_silence_rms_threshold: float
    stt_min_confidence: float
    stt_min_confidence_system_audio: float
    stt_short_text_min_confidence: float
    stt_short_text_min_confidence_system_audio: float
    stt_min_compact_length: int
    stt_max_repeat_ratio: float
    stt_max_repeat_ratio_system_audio: float
    stt_max_consecutive_repeat: int
    stt_max_consecutive_repeat_system_audio: int
    stt_min_repetition_tokens: int
    stt_min_repetition_tokens_system_audio: int
    stt_language_consistency_max_confidence: float
    stt_language_consistency_max_confidence_system_audio: float
    stt_min_target_script_ratio: float
    stt_min_target_script_ratio_system_audio: float
    stt_min_letter_ratio: float
    stt_min_letter_ratio_system_audio: float
    stt_duplicate_window_ms: int
    stt_duplicate_window_ms_system_audio: int
    stt_duplicate_similarity_threshold: float
    stt_duplicate_similarity_threshold_system_audio: float
    stt_duplicate_max_confidence: float
    stt_duplicate_max_confidence_system_audio: float
    stt_max_no_speech_prob: float | None
    stt_max_no_speech_prob_system_audio: float | None
    vad_frame_duration_ms: int
    vad_pre_roll_ms: int
    vad_post_roll_ms: int
    vad_post_roll_ms_system_audio: int
    vad_min_speech_ms: int
    vad_min_speech_ms_system_audio: int
    vad_max_segment_ms: int
    vad_min_activation_frames: int
    vad_min_activation_frames_system_audio: int
    vad_rms_threshold: float
    vad_rms_threshold_system_audio: float
    vad_adaptive_noise_floor_alpha: float
    vad_adaptive_threshold_multiplier: float
    vad_adaptive_threshold_multiplier_system_audio: float
    vad_active_threshold_ratio: float
    vad_active_threshold_ratio_system_audio: float
    vad_min_voiced_ratio: float
    vad_min_voiced_ratio_system_audio: float
    silero_vad_enabled: bool
    silero_vad_enabled_system_audio: bool
    silero_vad_threshold: float
    silero_vad_min_speech_ms: int
    ryzen_ai_installation_path: str | None
    analyzer_backend: str
    llm_provider_backend: str
    llm_model: str
    llm_base_url: str | None
    llm_api_key: str | None
    llm_timeout_seconds: int
    report_refiner_backend: str
    report_refiner_model: str
    report_refiner_base_url: str | None
    report_refiner_api_key: str | None
    report_refiner_timeout_seconds: int
    topic_summarizer_backend: str
    topic_summarizer_model: str
    topic_summarizer_base_url: str | None
    topic_summarizer_api_key: str | None
    topic_summarizer_timeout_seconds: int
    topic_summary_recent_utterance_count: int
    topic_summary_min_utterance_length: int
    topic_summary_min_utterance_confidence: float
    partial_buffer_ms: int
    partial_emit_interval_ms: int
    partial_min_rms_threshold: float
    partial_agreement_window: int
    partial_agreement_min_count: int
    partial_min_stable_chars: int
    partial_min_growth_chars: int
    partial_backtrack_tolerance_chars: int
    partial_commit_min_chars_without_boundary: int

    @classmethod
    def from_env(cls) -> "AppConfig":
        return cls(
            app_name=_get_env("APP_NAME", "meeting-overlay-assistant") or "meeting-overlay-assistant",
            app_env=_get_env("APP_ENV", "development") or "development",
            debug=_get_bool("DEBUG", True),
            database_path=_get_path("DATABASE_PATH", "backend/data/meeting_overlay.db"),
            log_level=_get_env("LOG_LEVEL", "INFO") or "INFO",
            log_json=_get_bool("LOG_JSON", False),
            cors_allowed_origins=_get_csv(
                "CORS_ALLOWED_ORIGINS",
                [
                    "http://127.0.0.1:1420",
                    "http://localhost:1420",
                    "http://127.0.0.1:8000",
                    "http://localhost:8000",
                ],
            ),
            analysis_rules_config_path=_get_path("ANALYSIS_RULES_CONFIG_PATH", "backend/config/analysis_rules.json"),
            transcription_guard_config_path=_get_path(
                "TRANSCRIPTION_GUARD_CONFIG_PATH",
                "backend/config/transcription_guard.json",
            ),
            audio_source_profiles_config_path=_get_path(
                "AUDIO_SOURCE_PROFILES_CONFIG_PATH",
                "backend/config/audio_source_profiles.json",
            ),
            ai_service_profiles_config_path=_get_path(
                "AI_SERVICE_PROFILES_CONFIG_PATH",
                "backend/config/ai_service_profiles.json",
            ),
            media_service_profiles_config_path=_get_path(
                "MEDIA_SERVICE_PROFILES_CONFIG_PATH",
                "backend/config/media_service_profiles.json",
            ),
            acceptance_profiles_config_path=_get_path(
                "ACCEPTANCE_PROFILES_CONFIG_PATH",
                "backend/config/acceptance_profiles.json",
            ),
            audio_preprocessor_backend=_get_env("AUDIO_PREPROCESSOR_BACKEND", "bypass") or "bypass",
            audio_preprocessor_model_path=_get_env("AUDIO_PREPROCESSOR_MODEL_PATH"),
            audio_preprocessor_atten_lim_db=_get_int("AUDIO_PREPROCESSOR_ATTEN_LIM_DB", 18),
            speaker_diarizer_backend=_get_env("SPEAKER_DIARIZER_BACKEND", "unknown_speaker") or "unknown_speaker",
            speaker_diarizer_model_id=_get_env(
                "SPEAKER_DIARIZER_MODEL_ID",
                "pyannote/speaker-diarization-community-1",
            )
            or "pyannote/speaker-diarization-community-1",
            speaker_diarizer_auth_token=_get_env("SPEAKER_DIARIZER_AUTH_TOKEN"),
            speaker_diarizer_device=_get_env("SPEAKER_DIARIZER_DEVICE", "cpu") or "cpu",
            speaker_diarizer_default_label=_get_env("SPEAKER_DIARIZER_DEFAULT_LABEL", "speaker-unknown")
            or "speaker-unknown",
            speaker_diarizer_worker_python=_get_env("SPEAKER_DIARIZER_WORKER_PYTHON"),
            speaker_diarizer_worker_script_path=_get_env("SPEAKER_DIARIZER_WORKER_SCRIPT_PATH"),
            speaker_diarizer_worker_timeout_seconds=_get_int("SPEAKER_DIARIZER_WORKER_TIMEOUT_SECONDS", 120),
            stt_backend=_get_env("STT_BACKEND", "faster_whisper") or "faster_whisper",
            stt_backend_system_audio=_get_env("STT_BACKEND_SYSTEM_AUDIO"),
            stt_model_id=_get_env("STT_MODEL_ID", "deepdml/faster-whisper-large-v3-turbo-ct2")
            or "deepdml/faster-whisper-large-v3-turbo-ct2",
            stt_model_path=_get_env("STT_MODEL_PATH"),
            stt_base_model_id=_get_env("STT_BASE_MODEL_ID", "openai/whisper-small") or "openai/whisper-small",
            stt_encoder_model_path=_get_env("STT_ENCODER_MODEL_PATH"),
            stt_decoder_model_path=_get_env("STT_DECODER_MODEL_PATH"),
            stt_encoder_rai_path=_get_env("STT_ENCODER_RAI_PATH"),
            stt_base_url=_get_env("STT_BASE_URL"),
            stt_api_key=_get_env("STT_API_KEY"),
            stt_timeout_seconds=_get_int("STT_TIMEOUT_SECONDS", 20),
            stt_preload_on_startup=_get_bool("STT_PRELOAD_ON_STARTUP", True),
            stt_language=_get_env("STT_LANGUAGE", "ko") or "ko",
            stt_initial_prompt=_get_env("STT_INITIAL_PROMPT"),
            stt_device=_get_env("STT_DEVICE", "auto") or "auto",
            stt_compute_type=_get_env("STT_COMPUTE_TYPE", "default") or "default",
            stt_cpu_threads=_get_int("STT_CPU_THREADS", 0),
            stt_beam_size=_get_int("STT_BEAM_SIZE", 1),
            stt_sample_rate_hz=_get_int("STT_SAMPLE_RATE_HZ", 16000),
            stt_sample_width_bytes=_get_int("STT_SAMPLE_WIDTH_BYTES", 2),
            stt_channels=_get_int("STT_CHANNELS", 1),
            stt_silence_rms_threshold=_get_float("STT_SILENCE_RMS_THRESHOLD", 0.003),
            stt_min_confidence=_get_float("STT_MIN_CONFIDENCE", 0.35),
            stt_min_confidence_system_audio=_get_float("STT_MIN_CONFIDENCE_SYSTEM_AUDIO", 0.6),
            stt_short_text_min_confidence=_get_float("STT_SHORT_TEXT_MIN_CONFIDENCE", 0.6),
            stt_short_text_min_confidence_system_audio=_get_float(
                "STT_SHORT_TEXT_MIN_CONFIDENCE_SYSTEM_AUDIO",
                0.8,
            ),
            stt_min_compact_length=_get_int("STT_MIN_COMPACT_LENGTH", 2),
            stt_max_repeat_ratio=_get_float("STT_MAX_REPEAT_RATIO", 0.6),
            stt_max_repeat_ratio_system_audio=_get_float("STT_MAX_REPEAT_RATIO_SYSTEM_AUDIO", 0.5),
            stt_max_consecutive_repeat=_get_int("STT_MAX_CONSECUTIVE_REPEAT", 4),
            stt_max_consecutive_repeat_system_audio=_get_int("STT_MAX_CONSECUTIVE_REPEAT_SYSTEM_AUDIO", 3),
            stt_min_repetition_tokens=_get_int("STT_MIN_REPETITION_TOKENS", 6),
            stt_min_repetition_tokens_system_audio=_get_int("STT_MIN_REPETITION_TOKENS_SYSTEM_AUDIO", 4),
            stt_language_consistency_max_confidence=_get_float(
                "STT_LANGUAGE_CONSISTENCY_MAX_CONFIDENCE",
                0.7,
            ),
            stt_language_consistency_max_confidence_system_audio=_get_float(
                "STT_LANGUAGE_CONSISTENCY_MAX_CONFIDENCE_SYSTEM_AUDIO",
                0.75,
            ),
            stt_min_target_script_ratio=_get_float("STT_MIN_TARGET_SCRIPT_RATIO", 0.35),
            stt_min_target_script_ratio_system_audio=_get_float(
                "STT_MIN_TARGET_SCRIPT_RATIO_SYSTEM_AUDIO",
                0.45,
            ),
            stt_min_letter_ratio=_get_float("STT_MIN_LETTER_RATIO", 0.45),
            stt_min_letter_ratio_system_audio=_get_float("STT_MIN_LETTER_RATIO_SYSTEM_AUDIO", 0.55),
            stt_duplicate_window_ms=_get_int("STT_DUPLICATE_WINDOW_MS", 2500),
            stt_duplicate_window_ms_system_audio=_get_int("STT_DUPLICATE_WINDOW_MS_SYSTEM_AUDIO", 8000),
            stt_duplicate_similarity_threshold=_get_float("STT_DUPLICATE_SIMILARITY_THRESHOLD", 0.98),
            stt_duplicate_similarity_threshold_system_audio=_get_float(
                "STT_DUPLICATE_SIMILARITY_THRESHOLD_SYSTEM_AUDIO",
                0.9,
            ),
            stt_duplicate_max_confidence=_get_float("STT_DUPLICATE_MAX_CONFIDENCE", 0.0),
            stt_duplicate_max_confidence_system_audio=_get_float(
                "STT_DUPLICATE_MAX_CONFIDENCE_SYSTEM_AUDIO",
                0.8,
            ),
            stt_max_no_speech_prob=_get_float("STT_MAX_NO_SPEECH_PROB", 1.0),
            stt_max_no_speech_prob_system_audio=_get_float(
                "STT_MAX_NO_SPEECH_PROB_SYSTEM_AUDIO",
                0.8,
            ),
            vad_frame_duration_ms=_get_int("VAD_FRAME_DURATION_MS", 30),
            vad_pre_roll_ms=_get_int("VAD_PRE_ROLL_MS", 300),
            vad_post_roll_ms=_get_int("VAD_POST_ROLL_MS", 450),
            vad_post_roll_ms_system_audio=_get_int("VAD_POST_ROLL_MS_SYSTEM_AUDIO", 650),
            vad_min_speech_ms=_get_int("VAD_MIN_SPEECH_MS", 240),
            vad_min_speech_ms_system_audio=_get_int("VAD_MIN_SPEECH_MS_SYSTEM_AUDIO", 180),
            vad_max_segment_ms=_get_int("VAD_MAX_SEGMENT_MS", 5000),
            vad_min_activation_frames=_get_int("VAD_MIN_ACTIVATION_FRAMES", 2),
            vad_min_activation_frames_system_audio=_get_int("VAD_MIN_ACTIVATION_FRAMES_SYSTEM_AUDIO", 2),
            vad_rms_threshold=_get_float("VAD_RMS_THRESHOLD", 0.01),
            vad_rms_threshold_system_audio=_get_float("VAD_RMS_THRESHOLD_SYSTEM_AUDIO", 0.008),
            vad_adaptive_noise_floor_alpha=_get_float("VAD_ADAPTIVE_NOISE_FLOOR_ALPHA", 0.92),
            vad_adaptive_threshold_multiplier=_get_float("VAD_ADAPTIVE_THRESHOLD_MULTIPLIER", 1.9),
            vad_adaptive_threshold_multiplier_system_audio=_get_float(
                "VAD_ADAPTIVE_THRESHOLD_MULTIPLIER_SYSTEM_AUDIO",
                1.55,
            ),
            vad_active_threshold_ratio=_get_float("VAD_ACTIVE_THRESHOLD_RATIO", 0.8),
            vad_active_threshold_ratio_system_audio=_get_float("VAD_ACTIVE_THRESHOLD_RATIO_SYSTEM_AUDIO", 0.72),
            vad_min_voiced_ratio=_get_float("VAD_MIN_VOICED_RATIO", 0.18),
            vad_min_voiced_ratio_system_audio=_get_float("VAD_MIN_VOICED_RATIO_SYSTEM_AUDIO", 0.12),
            silero_vad_enabled=_get_bool("SILERO_VAD_ENABLED", False),
            silero_vad_enabled_system_audio=_get_bool("SILERO_VAD_ENABLED_SYSTEM_AUDIO", False),
            silero_vad_threshold=_get_float("SILERO_VAD_THRESHOLD", 0.5),
            silero_vad_min_speech_ms=_get_int("SILERO_VAD_MIN_SPEECH_MS", 120),
            ryzen_ai_installation_path=_get_env("RYZEN_AI_INSTALLATION_PATH"),
            analyzer_backend=_get_env("ANALYZER_BACKEND", "insight_pipeline") or "insight_pipeline",
            llm_provider_backend=_get_env("LLM_PROVIDER_BACKEND", "ollama") or "ollama",
            llm_model=_get_env("LLM_MODEL", "qwen2.5:3b-instruct") or "qwen2.5:3b-instruct",
            llm_base_url=_get_env("LLM_BASE_URL"),
            llm_api_key=_get_env("LLM_API_KEY"),
            llm_timeout_seconds=_get_int("LLM_TIMEOUT_SECONDS", 20),
            report_refiner_backend=_get_env("REPORT_REFINER_BACKEND", "structured") or "structured",
            report_refiner_model=_get_env("REPORT_REFINER_MODEL", "qwen2.5:3b-instruct")
            or "qwen2.5:3b-instruct",
            report_refiner_base_url=_get_env("REPORT_REFINER_BASE_URL"),
            report_refiner_api_key=_get_env("REPORT_REFINER_API_KEY"),
            report_refiner_timeout_seconds=_get_int("REPORT_REFINER_TIMEOUT_SECONDS", 20),
            topic_summarizer_backend=_get_env("TOPIC_SUMMARIZER_BACKEND", "noop") or "noop",
            topic_summarizer_model=_get_env("TOPIC_SUMMARIZER_MODEL", "qwen2.5:3b-instruct")
            or "qwen2.5:3b-instruct",
            topic_summarizer_base_url=_get_env("TOPIC_SUMMARIZER_BASE_URL"),
            topic_summarizer_api_key=_get_env("TOPIC_SUMMARIZER_API_KEY"),
            topic_summarizer_timeout_seconds=_get_int("TOPIC_SUMMARIZER_TIMEOUT_SECONDS", 10),
            topic_summary_recent_utterance_count=_get_int("TOPIC_SUMMARY_RECENT_UTTERANCE_COUNT", 5),
            topic_summary_min_utterance_length=_get_int("TOPIC_SUMMARY_MIN_UTTERANCE_LENGTH", 10),
            topic_summary_min_utterance_confidence=_get_float("TOPIC_SUMMARY_MIN_UTTERANCE_CONFIDENCE", 0.58),
            partial_buffer_ms=_get_int("PARTIAL_BUFFER_MS", 900),
            partial_emit_interval_ms=_get_int("PARTIAL_EMIT_INTERVAL_MS", 240),
            partial_min_rms_threshold=_get_float("PARTIAL_MIN_RMS_THRESHOLD", 0.006),
            partial_agreement_window=_get_int("PARTIAL_AGREEMENT_WINDOW", 3),
            partial_agreement_min_count=_get_int("PARTIAL_AGREEMENT_MIN_COUNT", 2),
            partial_min_stable_chars=_get_int("PARTIAL_MIN_STABLE_CHARS", 2),
            partial_min_growth_chars=_get_int("PARTIAL_MIN_GROWTH_CHARS", 2),
            partial_backtrack_tolerance_chars=_get_int(
                "PARTIAL_BACKTRACK_TOLERANCE_CHARS",
                2,
            ),
            partial_commit_min_chars_without_boundary=_get_int(
                "PARTIAL_COMMIT_MIN_CHARS_WITHOUT_BOUNDARY",
                6,
            ),
        )


settings = AppConfig.from_env()
