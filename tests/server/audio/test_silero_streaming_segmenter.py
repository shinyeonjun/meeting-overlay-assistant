"""Silero 스트리밍 세그먼터 테스트.

실제 ONNX 모델 대신 진폭으로 음성 확률을 정하는 가짜 모델을 넣어 상태 전이만 검증한다.
"""

from __future__ import annotations

import numpy as np

from server.app.contexts.live_capture.application.audio.segmentation.silero_streaming_segmenter import (
    OnnxSileroSpeechProbabilityModel,
    SileroStreamingSegmenterConfig,
    SileroStreamingSpeechSegmenter,
)

SR = 16000


class _AmplitudeModel:
    """청크 평균 진폭이 크면 말소리로 본다."""

    def __init__(self) -> None:
        self.reset_count = 0

    def reset(self) -> None:
        self.reset_count += 1

    def probability(self, chunk) -> float:
        return 0.9 if float(np.mean(np.abs(chunk))) > 0.05 else 0.0


def _tone(seconds: float) -> np.ndarray:
    t = np.arange(int(seconds * SR)) / SR
    return (0.5 * np.sin(2 * np.pi * 220 * t)).astype(np.float32)


def _silence(seconds: float) -> np.ndarray:
    return np.zeros(int(seconds * SR), dtype=np.float32)


def _pcm(audio: np.ndarray) -> bytes:
    return (np.clip(audio, -1, 1) * 32767).astype("<i2").tobytes()


def _feed(segmenter, audio: np.ndarray, chunk_samples: int = 480):
    pcm = _pcm(audio)
    step = chunk_samples * 2
    segments = []
    for i in range(0, len(pcm), step):
        segments.extend(segmenter.split(pcm[i : i + step]))
    return segments


def _segmenter(**overrides) -> SileroStreamingSpeechSegmenter:
    config = SileroStreamingSegmenterConfig(**overrides)
    return SileroStreamingSpeechSegmenter(config, model=_AmplitudeModel())


class TestSileroStreamingSpeechSegmenter:
    def test_무음이_이어지면_발화를_한_구간으로_내보낸다(self) -> None:
        segmenter = _segmenter(min_silence_ms=300, speech_pad_ms=60)

        segments = _feed(segmenter, np.concatenate([_silence(0.5), _tone(1.0), _silence(0.6)]))

        assert len(segments) == 1
        duration_ms = segments[0].end_ms - segments[0].start_ms
        # 발화 1초 + 앞뒤 여유 60ms씩, 32ms 청크 경계 오차를 허용한다.
        assert 1000 <= duration_ms <= 1200
        audio_ms = len(segments[0].raw_bytes) / 2 / SR * 1000
        assert abs(audio_ms - duration_ms) <= 1

    def test_무음이_짧으면_구간을_닫지_않는다(self) -> None:
        segmenter = _segmenter(min_silence_ms=300)

        segments = _feed(segmenter, np.concatenate([_tone(0.8), _silence(0.15), _tone(0.8), _silence(0.5)]))

        assert len(segments) == 1

    def test_짧은_소리는_버린다(self) -> None:
        segmenter = _segmenter(min_speech_ms=240)

        segments = _feed(segmenter, np.concatenate([_silence(0.3), _tone(0.1), _silence(0.6)]))

        assert segments == []

    def test_쉼_없이_길게_말하면_최대_길이에서_나눈다(self) -> None:
        segmenter = _segmenter(max_segment_ms=2000)

        segments = _feed(segmenter, np.concatenate([_tone(5.0), _silence(0.6)]))

        assert len(segments) == 3
        assert all(s.end_ms - s.start_ms <= 2100 for s in segments)
        # 나눈 구간은 서로 겹치거나 비지 않고 이어진다.
        assert segments[0].end_ms == segments[1].start_ms
        assert segments[1].end_ms == segments[2].start_ms
        # 구간 끝 샘플 위치는 스트림 처음부터 센 값이다 (최대 2초 = 32000샘플마다 끊는다).
        assert [s.stream_end_sample for s in segments[:2]] == [32256, 64512]

    def test_조기_EOU_힌트는_확정_전에_한_번만_나온다(self) -> None:
        segmenter = _segmenter(min_silence_ms=600, early_eou_ms=200)

        assert _feed(segmenter, np.concatenate([_tone(1.0), _silence(0.3)])) == []
        assert segmenter.consume_early_eou_hint() is True
        assert segmenter.consume_early_eou_hint() is False

        segments = _feed(segmenter, _silence(0.5))
        assert len(segments) == 1
        assert segmenter.consume_early_eou_hint() is False

    def test_말이_다시_시작되면_조기_EOU_힌트를_거둔다(self) -> None:
        segmenter = _segmenter(min_silence_ms=600, early_eou_ms=200)

        _feed(segmenter, np.concatenate([_tone(1.0), _silence(0.3), _tone(0.2)]))

        assert segmenter.consume_early_eou_hint() is False

    def test_입력_청크_크기와_무관하게_같은_구간을_낸다(self) -> None:
        audio = np.concatenate([_silence(0.4), _tone(1.2), _silence(0.5), _tone(0.7), _silence(0.6)])
        a = _feed(_segmenter(), audio, chunk_samples=480)
        b = _feed(_segmenter(), audio, chunk_samples=1600)

        assert len(a) == len(b) == 2
        assert [len(s.raw_bytes) for s in a] == [len(s.raw_bytes) for s in b]

    def test_16kHz가_아니면_거부한다(self) -> None:
        try:
            SileroStreamingSpeechSegmenter(SileroStreamingSegmenterConfig(sample_rate_hz=8000), model=_AmplitudeModel())
        except ValueError:
            return
        raise AssertionError("8kHz 입력을 거부해야 합니다.")


def test_ONNX_모델은_무음보다_말소리에_높은_확률을_준다() -> None:
    model = OnnxSileroSpeechProbabilityModel()
    silence_prob = model.probability(np.zeros(512, dtype=np.float32))
    model.reset()
    # 사람 목소리 대신 성대 진동과 비슷한 주기 신호를 몇 청크 이어서 넣는다.
    rng = np.random.default_rng(0)
    t = np.arange(512 * 20) / SR
    voiced = (
        0.3 * np.sign(np.sin(2 * np.pi * 140 * t)) * (0.6 + 0.4 * np.sin(2 * np.pi * 4 * t))
        + 0.02 * rng.standard_normal(t.size)
    ).astype(np.float32)
    probs = [model.probability(voiced[i : i + 512]) for i in range(0, voiced.size, 512)]

    assert 0.0 <= silence_prob <= 1.0
    assert all(0.0 <= p <= 1.0 for p in probs)
    assert silence_prob < 0.5
