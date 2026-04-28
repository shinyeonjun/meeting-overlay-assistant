"""AppConfig AI/분석 섹션."""

from __future__ import annotations

from server.app.core.config_helpers.env import get_bool, get_env, get_float, get_int


def build_ai_values() -> dict[str, object]:
    """분석, 보고서, retrieval, topic summarizer 설정을 조립한다."""

    analyzer_backend = get_env("ANALYZER_BACKEND", "rule_based") or "rule_based"

    return {
        "analyzer_backend": analyzer_backend,
        "live_analyzer_backend": get_env("LIVE_ANALYZER_BACKEND", "noop") or "noop",
        "post_processing_analyzer_backend": (
            get_env("POST_PROCESSING_ANALYZER_BACKEND", "rule_based") or "rule_based"
        ),
        "report_analyzer_backend": get_env("REPORT_ANALYZER_BACKEND", "rule_based") or "rule_based",
        "llm_provider_backend": get_env("LLM_PROVIDER_BACKEND", "ollama") or "ollama",
        "llm_model": get_env("LLM_MODEL", "qwen2.5:3b-instruct") or "qwen2.5:3b-instruct",
        "llm_base_url": get_env("LLM_BASE_URL"),
        "llm_api_key": get_env("LLM_API_KEY"),
        "llm_timeout_seconds": get_int("LLM_TIMEOUT_SECONDS", 20),
        "note_transcript_stt_model_id": get_env(
            "NOTE_TRANSCRIPT_STT_MODEL_ID",
            "Systran/faster-whisper-large-v3",
        )
        or "Systran/faster-whisper-large-v3",
        "note_transcript_stt_model_path": get_env(
            "NOTE_TRANSCRIPT_STT_MODEL_PATH",
            "server/models/stt/faster-whisper-large-v3",
        ),
        "note_transcript_stt_beam_size": get_int(
            "NOTE_TRANSCRIPT_STT_BEAM_SIZE",
            5,
        ),
        "note_transcript_correction_enabled": get_bool(
            "NOTE_TRANSCRIPT_CORRECTION_ENABLED",
            False,
        ),
        "note_transcript_correction_backend": get_env(
            "NOTE_TRANSCRIPT_CORRECTION_BACKEND",
            "ollama",
        )
        or "ollama",
        "note_transcript_correction_model": get_env(
            "NOTE_TRANSCRIPT_CORRECTION_MODEL",
            "gemma4:e4b",
        )
        or "gemma4:e4b",
        "note_transcript_correction_base_url": get_env(
            "NOTE_TRANSCRIPT_CORRECTION_BASE_URL",
        ),
        "note_transcript_correction_api_key": get_env(
            "NOTE_TRANSCRIPT_CORRECTION_API_KEY",
        ),
        "note_transcript_correction_timeout_seconds": get_int(
            "NOTE_TRANSCRIPT_CORRECTION_TIMEOUT_SECONDS",
            30,
        ),
        "note_transcript_correction_max_window": get_int(
            "NOTE_TRANSCRIPT_CORRECTION_MAX_WINDOW",
            3,
        ),
        "note_transcript_correction_max_candidates": get_int(
            "NOTE_TRANSCRIPT_CORRECTION_MAX_CANDIDATES",
            12,
        ),
        "note_transcript_correction_max_confidence_for_correction": get_float(
            "NOTE_TRANSCRIPT_CORRECTION_MAX_CONFIDENCE_FOR_CORRECTION",
            0.72,
        ),
        "note_transcript_correction_short_utterance_max_chars": get_int(
            "NOTE_TRANSCRIPT_CORRECTION_SHORT_UTTERANCE_MAX_CHARS",
            12,
        ),
        "meeting_minutes_analyzer_backend": get_env(
            "MEETING_MINUTES_ANALYZER_BACKEND",
            "ollama",
        )
        or "ollama",
        "meeting_minutes_analyzer_profile": get_env(
            "MEETING_MINUTES_ANALYZER_PROFILE",
            "meeting_minutes_default",
        )
        or "meeting_minutes_default",
        "meeting_minutes_analyzer_model": get_env(
            "MEETING_MINUTES_ANALYZER_MODEL",
            "caps-meeting-minutes-gemma4",
        )
        or "caps-meeting-minutes-gemma4",
        "meeting_minutes_analyzer_base_url": get_env(
            "MEETING_MINUTES_ANALYZER_BASE_URL",
            "http://127.0.0.1:11434/v1",
        ),
        "meeting_minutes_analyzer_api_key": get_env(
            "MEETING_MINUTES_ANALYZER_API_KEY",
        ),
        "meeting_minutes_analyzer_timeout_seconds": get_int(
            "MEETING_MINUTES_ANALYZER_TIMEOUT_SECONDS",
            300,
        ),
        "meeting_minutes_analyzer_max_transcript_chars": get_int(
            "MEETING_MINUTES_ANALYZER_MAX_TRANSCRIPT_CHARS",
            8000,
        ),
        "meeting_minutes_analyzer_map_reduce_segment_threshold": get_int(
            "MEETING_MINUTES_ANALYZER_MAP_REDUCE_SEGMENT_THRESHOLD",
            36,
        ),
        "meeting_minutes_analyzer_max_segments_per_chunk": get_int(
            "MEETING_MINUTES_ANALYZER_MAX_SEGMENTS_PER_CHUNK",
            20,
        ),
        "retrieval_embedding_backend": get_env("RETRIEVAL_EMBEDDING_BACKEND", "noop") or "noop",
        "retrieval_embedding_model": get_env("RETRIEVAL_EMBEDDING_MODEL", "nomic-embed-text:latest")
        or "nomic-embed-text:latest",
        "retrieval_embedding_base_url": get_env("RETRIEVAL_EMBEDDING_BASE_URL", "http://127.0.0.1:11434"),
        "retrieval_embedding_timeout_seconds": get_int("RETRIEVAL_EMBEDDING_TIMEOUT_SECONDS", 20),
        "retrieval_embedding_dimensions": get_int("RETRIEVAL_EMBEDDING_DIMENSIONS", 768),
        "retrieval_chunk_target_chars": get_int("RETRIEVAL_CHUNK_TARGET_CHARS", 1000),
        "retrieval_chunk_overlap_chars": get_int("RETRIEVAL_CHUNK_OVERLAP_CHARS", 160),
        "retrieval_search_candidate_limit": get_int("RETRIEVAL_SEARCH_CANDIDATE_LIMIT", 100),
        "topic_summarizer_backend": get_env("TOPIC_SUMMARIZER_BACKEND", "noop") or "noop",
        "topic_summarizer_model": get_env("TOPIC_SUMMARIZER_MODEL", "qwen2.5:3b-instruct")
        or "qwen2.5:3b-instruct",
        "topic_summarizer_base_url": get_env("TOPIC_SUMMARIZER_BASE_URL"),
        "topic_summarizer_api_key": get_env("TOPIC_SUMMARIZER_API_KEY"),
        "topic_summarizer_timeout_seconds": get_int("TOPIC_SUMMARIZER_TIMEOUT_SECONDS", 10),
        "topic_summary_recent_utterance_count": get_int("TOPIC_SUMMARY_RECENT_UTTERANCE_COUNT", 5),
        "topic_summary_min_utterance_length": get_int("TOPIC_SUMMARY_MIN_UTTERANCE_LENGTH", 10),
        "topic_summary_min_utterance_confidence": get_float("TOPIC_SUMMARY_MIN_UTTERANCE_CONFIDENCE", 0.58),
        "workspace_summary_synthesizer_backend": (
            get_env("WORKSPACE_SUMMARY_SYNTHESIZER_BACKEND", "noop") or "noop"
        ),
        "workspace_summary_synthesizer_model": (
            get_env("WORKSPACE_SUMMARY_SYNTHESIZER_MODEL", "gemma4:e4b") or "gemma4:e4b"
        ),
        "workspace_summary_synthesizer_base_url": get_env(
            "WORKSPACE_SUMMARY_SYNTHESIZER_BASE_URL"
        ),
        "workspace_summary_synthesizer_api_key": get_env(
            "WORKSPACE_SUMMARY_SYNTHESIZER_API_KEY"
        ),
        "workspace_summary_synthesizer_timeout_seconds": get_int(
            "WORKSPACE_SUMMARY_SYNTHESIZER_TIMEOUT_SECONDS",
            90,
        ),
        "workspace_summary_wait_timeout_seconds": get_float(
            "WORKSPACE_SUMMARY_WAIT_TIMEOUT_SECONDS",
            300.0,
        ),
        "workspace_summary_poll_interval_seconds": get_float(
            "WORKSPACE_SUMMARY_POLL_INTERVAL_SECONDS",
            5.0,
        ),
        "assistant_tool_calling_enabled": get_bool(
            "ASSISTANT_TOOL_CALLING_ENABLED",
            False,
        ),
        "assistant_require_action_confirmation": get_bool(
            "ASSISTANT_REQUIRE_ACTION_CONFIRMATION",
            True,
        ),
    }
