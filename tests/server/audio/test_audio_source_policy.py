"""오디오 영역의 test audio source policy 동작을 검증한다."""
from __future__ import annotations

from server.app.api.http.wiring.audio_runtime_builders.segmentation import (
    build_transcription_guard,
)
from server.app.core.audio_source_policy import resolve_audio_source_policy
from server.app.core.config import settings
from server.app.domain.shared.enums import AudioSource
from server.app.services.audio.stt.transcription import TranscriptionResult


class TestAudioSourcePolicy:
    """입력 소스별 정책 차이를 검증한다."""

    def test_system_audio는_별도_guard를_사용한다(self) -> None:
        system_policy = resolve_audio_source_policy(AudioSource.SYSTEM_AUDIO.value, settings)
        mic_policy = resolve_audio_source_policy(AudioSource.MIC.value, settings)

        assert system_policy.vad_max_segment_ms == 1800
        assert mic_policy.vad_max_segment_ms == 1800
        assert system_policy.guard_max_no_speech_prob == 0.8
        assert mic_policy.guard_max_no_speech_prob == 1.0

    def test_system_audio는_live_caption용_정책을_가진다(self) -> None:
        policy = resolve_audio_source_policy(AudioSource.SYSTEM_AUDIO.value, settings)

        assert policy.preview_min_compact_length == 1
        assert policy.preview_backpressure_queue_delay_ms == 3000
        assert policy.preview_backpressure_hold_chunks == 2
        assert policy.segment_grace_match_max_gap_ms == 1400
        assert policy.live_final_emit_max_delay_ms == 3500
        assert policy.final_short_text_max_compact_length == 5
        assert policy.final_short_text_min_confidence == 0.58
        assert policy.vad_early_post_roll_ms == 210
        assert policy.vad_post_roll_ms == 420
        assert policy.vad_min_speech_ms == 220

    def test_mic_and_audio는_system_audio_정책을_따른다(self) -> None:
        mixed_policy = resolve_audio_source_policy(AudioSource.MIC_AND_AUDIO.value, settings)
        system_policy = resolve_audio_source_policy(AudioSource.SYSTEM_AUDIO.value, settings)

        assert mixed_policy.use_vad == system_policy.use_vad
        assert mixed_policy.vad_early_post_roll_ms == system_policy.vad_early_post_roll_ms
        assert mixed_policy.vad_post_roll_ms == system_policy.vad_post_roll_ms
        assert mixed_policy.vad_min_speech_ms == system_policy.vad_min_speech_ms
        assert mixed_policy.preview_backpressure_queue_delay_ms == system_policy.preview_backpressure_queue_delay_ms
        assert mixed_policy.live_final_emit_max_delay_ms == system_policy.live_final_emit_max_delay_ms
        assert mixed_policy.final_short_text_min_confidence == system_policy.final_short_text_min_confidence

    def test_file은_노트_후처리에서도_차단_문구_guard를_사용한다(self) -> None:
        file_policy = resolve_audio_source_policy(AudioSource.FILE.value, settings)

        assert file_policy.guard_blocked_phrases_enabled is True

    def test_file_guard는_high_confidence_outro도_막는다(self) -> None:
        file_policy = resolve_audio_source_policy(AudioSource.FILE.value, settings)
        guard = build_transcription_guard(source_policy=file_policy, settings=settings)

        assert not guard.should_keep(
            TranscriptionResult(
                text="시청해주셔서 감사합니다.",
                confidence=0.95,
            )
        )
