"""오디오 세그먼터 테스트."""

from __future__ import annotations

import numpy as np

from backend.app.services.audio.segmentation.speech_segmenter import (
    SpeechSegmenter,
    VadSegmenterConfig,
    VadSpeechSegmenter,
)


def _pcm_frame(value: float, sample_count: int) -> bytes:
    samples = np.full(sample_count, value, dtype=np.float32)
    pcm16 = (np.clip(samples, -1.0, 1.0) * 32767.0).astype(np.int16)
    return pcm16.tobytes()


class TestSpeechSegmenter:
    """오디오 세그먼터 동작을 검증한다."""

    def test_기본_세그먼터는_chunk를_그대로_하나의_세그먼트로_반환한다(self):
        segmenter = SpeechSegmenter()

        segments = segmenter.split(b"hello")

        assert len(segments) == 1
        assert segments[0].raw_bytes == b"hello"

    def test_vad_세그먼터는_무음과_발화를_구분해_세그먼트를_만든다(self):
        config = VadSegmenterConfig(
            sample_rate_hz=1000,
            sample_width_bytes=2,
            channels=1,
            frame_duration_ms=100,
            pre_roll_ms=100,
            post_roll_ms=200,
            min_speech_ms=200,
            max_segment_ms=1000,
            min_activation_frames=2,
            rms_threshold=0.05,
        )
        segmenter = VadSpeechSegmenter(config)
        silence = _pcm_frame(0.0, config.frame_sample_count)
        speech = _pcm_frame(0.6, config.frame_sample_count)

        assert segmenter.split(silence) == []
        assert segmenter.split(speech) == []
        assert segmenter.split(speech) == []
        assert segmenter.split(speech) == []
        assert segmenter.split(silence) == []

        segments = segmenter.split(silence)

        assert len(segments) == 1
        assert segments[0].end_ms > segments[0].start_ms
        assert len(segments[0].raw_bytes) % config.bytes_per_frame == 0
        assert len(segments[0].raw_bytes) >= config.bytes_per_frame * config.min_speech_frames

    def test_vad_세그먼터는_너무_짧은_소리는_버린다(self):
        config = VadSegmenterConfig(
            sample_rate_hz=1000,
            sample_width_bytes=2,
            channels=1,
            frame_duration_ms=100,
            pre_roll_ms=100,
            post_roll_ms=200,
            min_speech_ms=300,
            max_segment_ms=1000,
            min_activation_frames=2,
            rms_threshold=0.05,
        )
        segmenter = VadSpeechSegmenter(config)
        silence = _pcm_frame(0.0, config.frame_sample_count)
        speech = _pcm_frame(0.6, config.frame_sample_count)

        assert segmenter.split(speech) == []
        assert segmenter.split(speech) == []
        assert segmenter.split(silence) == []

        segments = segmenter.split(silence)

        assert segments == []

    def test_vad_세그먼터는_final_eou_전에_early_eou_힌트를_한번_낸다(self):
        config = VadSegmenterConfig(
            sample_rate_hz=1000,
            sample_width_bytes=2,
            channels=1,
            frame_duration_ms=100,
            pre_roll_ms=100,
            early_post_roll_ms=200,
            post_roll_ms=400,
            min_speech_ms=200,
            max_segment_ms=1000,
            min_activation_frames=2,
            rms_threshold=0.05,
        )
        segmenter = VadSpeechSegmenter(config)
        silence = _pcm_frame(0.0, config.frame_sample_count)
        speech = _pcm_frame(0.6, config.frame_sample_count)

        assert segmenter.split(speech) == []
        assert segmenter.split(speech) == []
        assert segmenter.consume_early_eou_hint() is False

        assert segmenter.split(silence) == []
        assert segmenter.consume_early_eou_hint() is False

        assert segmenter.split(silence) == []
        assert segmenter.consume_early_eou_hint() is True
        assert segmenter.consume_early_eou_hint() is False

        segments = []
        for _ in range(8):
            segments = segmenter.split(silence)
            if segments:
                break

        assert len(segments) == 1
        assert segmenter.consume_early_eou_hint() is False

