"""AppConfig 기본 섹션."""

from __future__ import annotations

from server.app.core.config_helpers.env import (
    get_bool,
    get_csv,
    get_env,
    get_float,
    get_int,
    get_path,
)


def build_base_values() -> dict[str, object]:
    """앱 기본값, 경로, 로그, 인증 설정을 조립한다."""

    return {
        "app_name": get_env("APP_NAME", "meeting-overlay-assistant") or "meeting-overlay-assistant",
        "app_env": get_env("APP_ENV", "development") or "development",
        "debug": get_bool("DEBUG", True),
        "persistence_backend": get_env("PERSISTENCE_BACKEND", "postgresql") or "postgresql",
        "database_path": get_path("DATABASE_PATH", "server/data/meeting_overlay.db"),
        "postgresql_dsn": get_env("POSTGRESQL_DSN"),
        "redis_url": get_env("REDIS_URL"),
        "artifacts_root_path": get_path("ARTIFACTS_ROOT_PATH", "server/data/artifacts"),
        "session_post_processing_job_queue_key": get_env(
            "SESSION_POST_PROCESSING_JOB_QUEUE_KEY",
            "caps:queue:session-post-processing",
        )
        or "caps:queue:session-post-processing",
        "session_post_processing_job_queue_block_seconds": get_int(
            "SESSION_POST_PROCESSING_JOB_QUEUE_BLOCK_SECONDS",
            15,
        ),
        "session_post_processing_job_fallback_poll_seconds": get_int(
            "SESSION_POST_PROCESSING_JOB_FALLBACK_POLL_SECONDS",
            30,
        ),
        "session_post_processing_live_wait_timeout_seconds": get_float(
            "SESSION_POST_PROCESSING_LIVE_WAIT_TIMEOUT_SECONDS",
            300.0,
        ),
        "session_post_processing_live_poll_interval_seconds": get_float(
            "SESSION_POST_PROCESSING_LIVE_POLL_INTERVAL_SECONDS",
            5.0,
        ),
        "report_job_queue_key": get_env("REPORT_JOB_QUEUE_KEY", "caps:queue:report-generation")
        or "caps:queue:report-generation",
        "report_job_queue_block_seconds": get_int("REPORT_JOB_QUEUE_BLOCK_SECONDS", 15),
        "report_job_fallback_poll_seconds": get_int("REPORT_JOB_FALLBACK_POLL_SECONDS", 30),
        "note_correction_job_queue_key": get_env(
            "NOTE_CORRECTION_JOB_QUEUE_KEY",
            "caps:queue:note-correction",
        )
        or "caps:queue:note-correction",
        "note_correction_job_queue_block_seconds": get_int(
            "NOTE_CORRECTION_JOB_QUEUE_BLOCK_SECONDS",
            15,
        ),
        "note_correction_job_fallback_poll_seconds": get_int(
            "NOTE_CORRECTION_JOB_FALLBACK_POLL_SECONDS",
            30,
        ),
        "pipeline_job_max_attempts": get_int(
            "PIPELINE_JOB_MAX_ATTEMPTS",
            3,
        ),
        "pipeline_job_heartbeat_interval_seconds": get_int(
            "PIPELINE_JOB_HEARTBEAT_INTERVAL_SECONDS",
            15,
        ),
        "pipeline_recovery_session_limit": get_int(
            "PIPELINE_RECOVERY_SESSION_LIMIT",
            500,
        ),
        "live_question_analysis_enabled": get_bool("LIVE_QUESTION_ANALYSIS_ENABLED", False),
        "live_question_request_stream_key": get_env(
            "LIVE_QUESTION_REQUEST_STREAM_KEY",
            "caps:live_question:requests",
        )
        or "caps:live_question:requests",
        "live_question_result_stream_key": get_env(
            "LIVE_QUESTION_RESULT_STREAM_KEY",
            "caps:live_question:results",
        )
        or "caps:live_question:results",
        "live_question_stream_block_seconds": get_int(
            "LIVE_QUESTION_STREAM_BLOCK_SECONDS",
            5,
        ),
        "live_question_debounce_ms": get_int("LIVE_QUESTION_DEBOUNCE_MS", 600),
        "live_question_window_size": get_int("LIVE_QUESTION_WINDOW_SIZE", 4),
        "live_question_llm_backend": get_env(
            "LIVE_QUESTION_LLM_BACKEND",
            "ollama",
        )
        or "ollama",
        "live_question_llm_model": get_env(
            "LIVE_QUESTION_LLM_MODEL",
            "qwen2.5:3b-instruct",
        )
        or "qwen2.5:3b-instruct",
        "live_question_llm_base_url": get_env(
            "LIVE_QUESTION_LLM_BASE_URL",
            "http://127.0.0.1:11434/v1",
        ),
        "live_question_llm_api_key": get_env("LIVE_QUESTION_LLM_API_KEY"),
        "live_question_llm_timeout_seconds": get_int(
            "LIVE_QUESTION_LLM_TIMEOUT_SECONDS",
            20,
        ),
        "live_question_llm_keep_alive": get_env(
            "LIVE_QUESTION_LLM_KEEP_ALIVE",
            "30m",
        )
        or "30m",
        "log_file_path": get_path("LOG_FILE_PATH", "server/data/logs/caps-server.log"),
        "log_level": get_env("LOG_LEVEL", "INFO") or "INFO",
        "log_json": get_bool("LOG_JSON", False),
        "cors_allowed_origins": get_csv(
            "CORS_ALLOWED_ORIGINS",
            [
                "http://127.0.0.1:1420",
                "http://localhost:1420",
                "http://127.0.0.1:1430",
                "http://localhost:1430",
                "http://127.0.0.1:1431",
                "http://localhost:1431",
                "http://127.0.0.1:8000",
                "http://localhost:8000",
            ],
        ),
        "auth_enabled": get_bool("AUTH_ENABLED", False),
        "auth_session_ttl_hours": get_int("AUTH_SESSION_TTL_HOURS", 12),
        "analysis_rules_config_path": get_path("ANALYSIS_RULES_CONFIG_PATH", "server/config/analysis_rules.json"),
        "transcription_guard_config_path": get_path(
            "TRANSCRIPTION_GUARD_CONFIG_PATH",
            "server/config/transcription_guard.json",
        ),
        "audio_source_profiles_config_path": get_path(
            "AUDIO_SOURCE_PROFILES_CONFIG_PATH",
            "server/config/audio_source_profiles.json",
        ),
        "ai_service_profiles_config_path": get_path(
            "AI_SERVICE_PROFILES_CONFIG_PATH",
            "server/config/ai_service_profiles.json",
        ),
        "media_service_profiles_config_path": get_path(
            "MEDIA_SERVICE_PROFILES_CONFIG_PATH",
            "server/config/media_service_profiles.json",
        ),
        "acceptance_profiles_config_path": get_path(
            "ACCEPTANCE_PROFILES_CONFIG_PATH",
            "server/config/acceptance_profiles.json",
        ),
    }
