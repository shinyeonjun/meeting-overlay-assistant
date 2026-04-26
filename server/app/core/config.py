"""애플리케이션 전역 설정을 조합하고 노출한다."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from server.app.core.config_helpers.app_config_values import build_app_config_values
from server.app.core.config_helpers.env import ENV_PATH, ROOT_DIR, ensure_env_loaded


ensure_env_loaded()


@dataclass(frozen=True)
class AppConfig:
    """서버와 워커가 공유하는 최종 런타임 설정 묶음이다."""
    app_name: str
    app_env: str
    debug: bool
    persistence_backend: str
    database_path: Path
    postgresql_dsn: str | None
    redis_url: str | None
    artifacts_root_path: Path
    session_post_processing_job_queue_key: str
    session_post_processing_job_queue_block_seconds: int
    session_post_processing_job_fallback_poll_seconds: int
    report_job_queue_key: str
    report_job_queue_block_seconds: int
    report_job_fallback_poll_seconds: int
    note_correction_job_queue_key: str
    note_correction_job_queue_block_seconds: int
    note_correction_job_fallback_poll_seconds: int
    pipeline_job_max_attempts: int
    pipeline_job_heartbeat_interval_seconds: int
    pipeline_recovery_session_limit: int
    live_question_analysis_enabled: bool
    live_question_request_stream_key: str
    live_question_result_stream_key: str
    live_question_stream_block_seconds: int
    live_question_debounce_ms: int
    live_question_window_size: int
    live_question_llm_backend: str
    live_question_llm_model: str
    live_question_llm_base_url: str | None
    live_question_llm_api_key: str | None
    live_question_llm_timeout_seconds: int
    live_question_llm_keep_alive: str | None
    log_file_path: Path
    log_level: str
    log_json: bool
    cors_allowed_origins: list[str]
    auth_enabled: bool
    auth_session_ttl_hours: int
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
    mic_server_stt_fallback_enabled: bool
    mic_server_stt_preload_enabled: bool
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
    live_analyzer_backend: str
    post_processing_analyzer_backend: str
    report_analyzer_backend: str
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
    note_transcript_stt_model_id: str
    note_transcript_stt_model_path: str | None
    note_transcript_stt_beam_size: int
    note_transcript_correction_enabled: bool
    note_transcript_correction_backend: str
    note_transcript_correction_model: str
    note_transcript_correction_base_url: str | None
    note_transcript_correction_api_key: str | None
    note_transcript_correction_timeout_seconds: int
    note_transcript_correction_max_window: int
    note_transcript_correction_max_candidates: int
    note_transcript_correction_max_confidence_for_correction: float
    note_transcript_correction_short_utterance_max_chars: int
    retrieval_embedding_backend: str
    retrieval_embedding_model: str
    retrieval_embedding_base_url: str | None
    retrieval_embedding_timeout_seconds: int
    retrieval_embedding_dimensions: int
    retrieval_chunk_target_chars: int
    retrieval_chunk_overlap_chars: int
    retrieval_search_candidate_limit: int
    topic_summarizer_backend: str
    topic_summarizer_model: str
    topic_summarizer_base_url: str | None
    topic_summarizer_api_key: str | None
    topic_summarizer_timeout_seconds: int
    topic_summary_recent_utterance_count: int
    topic_summary_min_utterance_length: int
    topic_summary_min_utterance_confidence: float
    workspace_summary_synthesizer_backend: str
    workspace_summary_synthesizer_model: str
    workspace_summary_synthesizer_base_url: str | None
    workspace_summary_synthesizer_api_key: str | None
    workspace_summary_synthesizer_timeout_seconds: int
    workspace_summary_wait_timeout_seconds: float
    workspace_summary_poll_interval_seconds: float
    session_post_processing_live_wait_timeout_seconds: float
    session_post_processing_live_poll_interval_seconds: float
    partial_buffer_ms: int
    partial_emit_interval_ms: int
    partial_min_rms_threshold: float
    partial_agreement_window: int
    partial_agreement_min_count: int
    partial_min_stable_chars: int
    partial_min_growth_chars: int
    partial_backtrack_tolerance_chars: int
    partial_commit_min_chars_without_boundary: int
    live_stream_worker_count: int
    live_stream_pending_chunks_per_stream: int
    live_stream_max_running_sessions: int
    live_stream_max_running_mic_streams: int
    live_stream_max_running_system_audio_streams: int

    @classmethod
    def from_env(cls) -> "AppConfig":
        return cls(**build_app_config_values())


settings = AppConfig.from_env()
