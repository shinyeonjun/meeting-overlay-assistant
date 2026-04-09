"""audio runtime segmentation, guard, gate builder."""

from __future__ import annotations

from dataclasses import replace

from server.app.services.audio.filters.audio_content_gate import (
    AudioContentGate,
    AudioContentGateProfile,
)
from server.app.services.audio.filters.transcription_guard import (
    TranscriptionGuard,
    TranscriptionGuardConfig,
)
from server.app.services.audio.segmentation.silero_vad_segmenter import (
    SileroValidatedSpeechSegmenter,
    SileroVadValidatorConfig,
)
from server.app.services.audio.segmentation.speech_segmenter import (
    SpeechSegmenter,
    VadSegmenterConfig,
    VadSpeechSegmenter,
)


def build_audio_segmenter(*, source_policy, settings):
    """오디오 segmenter를 현재 설정으로 조립한다."""

    segmenter = SpeechSegmenter()
    if source_policy.use_vad:
        segmenter = VadSpeechSegmenter(
            VadSegmenterConfig(
                sample_rate_hz=settings.stt_sample_rate_hz,
                sample_width_bytes=settings.stt_sample_width_bytes,
                channels=settings.stt_channels,
                frame_duration_ms=settings.vad_frame_duration_ms,
                pre_roll_ms=settings.vad_pre_roll_ms,
                early_post_roll_ms=source_policy.vad_early_post_roll_ms,
                post_roll_ms=source_policy.vad_post_roll_ms,
                min_speech_ms=source_policy.vad_min_speech_ms,
                max_segment_ms=source_policy.vad_max_segment_ms,
                min_activation_frames=source_policy.vad_min_activation_frames,
                rms_threshold=source_policy.vad_rms_threshold,
                adaptive_noise_floor_alpha=settings.vad_adaptive_noise_floor_alpha,
                adaptive_threshold_multiplier=source_policy.vad_adaptive_threshold_multiplier,
                active_threshold_ratio=source_policy.vad_active_threshold_ratio,
                min_voiced_ratio=source_policy.vad_min_voiced_ratio,
            )
        )
    if source_policy.silero_vad_enabled:
        segmenter = SileroValidatedSpeechSegmenter(
            base_segmenter=segmenter,
            config=SileroVadValidatorConfig(
                sample_rate_hz=settings.stt_sample_rate_hz,
                sample_width_bytes=settings.stt_sample_width_bytes,
                channels=settings.stt_channels,
                threshold=settings.silero_vad_threshold,
                min_speech_duration_ms=settings.silero_vad_min_speech_ms,
            ),
        )
    return segmenter


def build_audio_content_gate(*, source_policy, settings) -> AudioContentGate:
    """audio content gate를 현재 설정으로 조립한다."""

    return AudioContentGate(
        AudioContentGateProfile(
            enabled=source_policy.content_gate_enabled,
            sample_rate_hz=settings.stt_sample_rate_hz,
            sample_width_bytes=settings.stt_sample_width_bytes,
            channels=settings.stt_channels,
            min_rms=source_policy.content_gate_min_rms,
            min_speech_band_ratio=source_policy.content_gate_min_speech_band_ratio,
            min_spectral_flatness=source_policy.content_gate_min_spectral_flatness,
            min_zero_crossing_rate=source_policy.content_gate_min_zero_crossing_rate,
        )
    )


def build_transcription_guard(*, source_policy, settings) -> TranscriptionGuard:
    """transcription guard를 현재 설정으로 조립한다."""

    config = TranscriptionGuardConfig.with_patterns_from_path(
        settings.transcription_guard_config_path,
        min_confidence=source_policy.guard_min_confidence,
        short_text_min_confidence=source_policy.guard_short_text_min_confidence,
        min_compact_length=settings.stt_min_compact_length,
        max_repeat_ratio=source_policy.guard_max_repeat_ratio,
        max_consecutive_repeat=source_policy.guard_max_consecutive_repeat,
        min_repetition_tokens=source_policy.guard_min_repetition_tokens,
        expected_language=settings.stt_language,
        language_consistency_enabled=source_policy.guard_language_consistency_enabled,
        language_consistency_max_confidence=source_policy.guard_language_consistency_max_confidence,
        min_target_script_ratio=source_policy.guard_min_target_script_ratio,
        min_letter_ratio=source_policy.guard_min_letter_ratio,
        max_no_speech_prob=source_policy.guard_max_no_speech_prob,
    )
    if source_policy.source == "file":
        # 노트 후처리는 CTA/아웃트로 hallucination이 들어오면 품질을 크게 해치므로 confidence와 무관하게 hard-block 한다.
        config = replace(config, blocked_phrase_max_confidence=1.0)
    if not source_policy.guard_blocked_phrases_enabled:
        config = TranscriptionGuardConfig(
            min_confidence=config.min_confidence,
            short_text_min_confidence=config.short_text_min_confidence,
            min_compact_length=config.min_compact_length,
            max_repeat_ratio=config.max_repeat_ratio,
            max_consecutive_repeat=config.max_consecutive_repeat,
            min_repetition_tokens=config.min_repetition_tokens,
            boundary_terms=config.boundary_terms,
            blocked_phrases=(),
            blocked_phrase_max_confidence=config.blocked_phrase_max_confidence,
            token_split_pattern=config.token_split_pattern,
            expected_language=config.expected_language,
            language_consistency_enabled=config.language_consistency_enabled,
            language_consistency_max_confidence=config.language_consistency_max_confidence,
            min_target_script_ratio=config.min_target_script_ratio,
            min_letter_ratio=config.min_letter_ratio,
            max_no_speech_prob=config.max_no_speech_prob,
        )
    return TranscriptionGuard(config)
