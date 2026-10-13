"""Silero VAD로 발화 구간을 직접 자르는 스트리밍 세그먼터.

에너지 기반 VadSpeechSegmenter와 같은 AudioSegmenter 규약(split)을 따른다.
Silero 모델은 faster-whisper가 내장한 Silero v6 ONNX를 onnxruntime으로 돌리므로
torch 없이 동작한다. 32ms(512 샘플) 단위로 음성 확률을 구하고, 무음이 일정 시간
이어지거나 구간이 최대 길이에 닿으면 SpeechSegment를 내보낸다.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from server.app.contexts.live_capture.application.audio.segmentation.models import SpeechSegment
from server.app.contexts.live_capture.application.audio.segmentation.vad_math import now_ms

SILERO_CHUNK_SAMPLES = 512
SILERO_CONTEXT_SAMPLES = 64
SILERO_SAMPLE_RATE_HZ = 16000


@dataclass(frozen=True)
class SileroStreamingSegmenterConfig:
    """Silero 스트리밍 세그먼터 설정."""

    sample_rate_hz: int = SILERO_SAMPLE_RATE_HZ
    sample_width_bytes: int = 2
    channels: int = 1
    threshold: float = 0.5
    min_silence_ms: int = 300
    early_eou_ms: int = 210
    max_segment_ms: int = 12000
    min_speech_ms: int = 240
    speech_pad_ms: int = 60


class SpeechProbabilityModel(Protocol):
    """512 샘플 청크의 음성 확률을 돌려주는 모델."""

    def reset(self) -> None:
        """내부 순환 상태를 비운다."""

    def probability(self, chunk) -> float:
        """float32 512 샘플(16kHz) 청크의 음성 확률(0~1)."""


class OnnxSileroSpeechProbabilityModel:
    """faster-whisper에 들어 있는 Silero v6 ONNX 모델을 스트리밍으로 호출한다."""

    def __init__(self, model_path: str | None = None) -> None:
        import numpy as np

        self._np = np
        self._session = self._create_session(model_path or self._default_model_path())
        self.reset()

    def reset(self) -> None:
        np = self._np
        self._h = np.zeros((1, 1, 128), dtype=np.float32)
        self._c = np.zeros((1, 1, 128), dtype=np.float32)
        self._context = np.zeros((1, SILERO_CONTEXT_SAMPLES), dtype=np.float32)

    def probability(self, chunk) -> float:
        np = self._np
        frame = np.asarray(chunk, dtype=np.float32).reshape(1, SILERO_CHUNK_SAMPLES)
        model_input = np.concatenate([self._context, frame], axis=1)
        output, self._h, self._c = self._session.run(None, {"input": model_input, "h": self._h, "c": self._c})
        self._context = frame[:, -SILERO_CONTEXT_SAMPLES:]
        return float(np.asarray(output).reshape(-1)[0])

    @staticmethod
    def _default_model_path() -> str:
        try:
            from faster_whisper.utils import get_assets_path
        except ImportError as error:  # pragma: no cover - 선택 의존성
            raise RuntimeError("Silero 세그먼터는 faster-whisper에 들어 있는 Silero VAD 모델을 사용합니다.") from error
        import os

        return os.path.join(get_assets_path(), "silero_vad_v6.onnx")

    @staticmethod
    def _create_session(model_path: str):
        try:
            import onnxruntime
        except ImportError as error:  # pragma: no cover - 선택 의존성
            raise RuntimeError("Silero 세그먼터를 사용하려면 onnxruntime 패키지가 필요합니다.") from error
        options = onnxruntime.SessionOptions()
        options.inter_op_num_threads = 1
        options.intra_op_num_threads = 1
        options.log_severity_level = 4
        return onnxruntime.InferenceSession(model_path, providers=["CPUExecutionProvider"], sess_options=options)


class SileroStreamingSpeechSegmenter:
    """PCM16 입력을 Silero 확률로 감지해서 발화 세그먼트로 묶는다."""

    def __init__(
        self,
        config: SileroStreamingSegmenterConfig,
        model: SpeechProbabilityModel | None = None,
    ) -> None:
        if config.sample_rate_hz != SILERO_SAMPLE_RATE_HZ:
            raise ValueError("Silero 스트리밍 세그먼터는 16kHz 입력만 지원합니다.")
        import numpy as np

        self._np = np
        self._config = config
        self._model = model if model is not None else OnnxSileroSpeechProbabilityModel()
        self._model.reset()

        rate = config.sample_rate_hz
        self._min_silence = int(rate * config.min_silence_ms / 1000)
        self._early_eou = int(rate * config.early_eou_ms / 1000)
        self._max_segment = max(int(rate * config.max_segment_ms / 1000), SILERO_CHUNK_SAMPLES)
        self._min_speech = int(rate * config.min_speech_ms / 1000)
        self._pad = int(rate * config.speech_pad_ms / 1000)
        self._negative_threshold = max(config.threshold - 0.15, 0.01)

        self._base_ms = now_ms()
        self._remainder = bytearray()
        self._samples = np.zeros(0, dtype=np.float32)  # self._buffer_start부터 들어온 샘플
        self._buffer_start = 0
        self._processed = 0

        self._triggered = False
        self._start = 0
        self._temp_end = 0
        self._voiced = 0
        self._early_hint_given = False
        self._pending_early_eou_hint = False

    def split(self, chunk: bytes) -> list[SpeechSegment]:
        if not chunk:
            return []
        self._remainder.extend(chunk)
        frame_bytes = SILERO_CHUNK_SAMPLES * self._config.sample_width_bytes * self._config.channels
        segments: list[SpeechSegment] = []
        while len(self._remainder) >= frame_bytes:
            raw = bytes(self._remainder[:frame_bytes])
            del self._remainder[:frame_bytes]
            segment = self._consume_chunk(self._to_mono_float(raw))
            if segment is not None:
                segments.append(segment)
        return segments

    def consume_early_eou_hint(self) -> bool:
        """live 확정용 early EOU 힌트를 1회성으로 소비한다."""

        if not self._pending_early_eou_hint:
            return False
        self._pending_early_eou_hint = False
        return True

    def _consume_chunk(self, frame) -> SpeechSegment | None:
        np = self._np
        self._samples = np.concatenate([self._samples, frame])
        self._processed += SILERO_CHUNK_SAMPLES
        current = self._processed
        probability = self._model.probability(frame)
        emitted: SpeechSegment | None = None

        if probability >= self._config.threshold:
            self._temp_end = 0
            self._pending_early_eou_hint = False
            self._early_hint_given = False
            if not self._triggered:
                self._triggered = True
                self._start = max(self._buffer_start, current - SILERO_CHUNK_SAMPLES - self._pad)
                self._voiced = 0
            self._voiced += SILERO_CHUNK_SAMPLES
        elif self._triggered and probability < self._negative_threshold:
            if not self._temp_end:
                self._temp_end = current - SILERO_CHUNK_SAMPLES
            silence = current - self._temp_end
            if not self._early_hint_given and silence >= self._early_eou:
                self._pending_early_eou_hint = True
                self._early_hint_given = True
            if silence >= self._min_silence:
                end = min(self._temp_end + self._pad, current)
                emitted = self._emit(self._start, end)
                self._reset_active()

        if self._triggered and current - self._start >= self._max_segment:
            # 쉼 없이 길게 말하면 최대 길이에서 끊고 같은 발화를 이어서 받는다.
            emitted = self._emit(self._start, current)
            self._start = current
            self._voiced = 0
            self._temp_end = 0
            self._drop_before(self._start)

        if not self._triggered:
            self._trim_idle_buffer()
        return emitted

    def _emit(self, start: int, end: int) -> SpeechSegment | None:
        if end <= start or self._voiced < self._min_speech:
            return None
        np = self._np
        offset_start = start - self._buffer_start
        offset_end = end - self._buffer_start
        audio = self._samples[offset_start:offset_end]
        pcm = (np.clip(audio, -1.0, 1.0) * 32767.0).astype("<i2").tobytes()
        rate_khz = self._config.sample_rate_hz / 1000
        return SpeechSegment(
            raw_bytes=pcm,
            start_ms=self._base_ms + int(start / rate_khz),
            end_ms=self._base_ms + int(end / rate_khz),
            stream_end_sample=end,
        )

    def _reset_active(self) -> None:
        self._triggered = False
        self._temp_end = 0
        self._voiced = 0
        self._early_hint_given = False
        self._pending_early_eou_hint = False

    def _trim_idle_buffer(self) -> None:
        # 다음 발화 시작에 붙일 앞쪽 여유(pad)만 남기고 버린다.
        keep = self._pad + SILERO_CHUNK_SAMPLES
        if len(self._samples) > keep:
            self._drop_before(self._buffer_start + len(self._samples) - keep)

    def _drop_before(self, sample_index: int) -> None:
        drop = sample_index - self._buffer_start
        if drop > 0:
            self._samples = self._samples[drop:]
            self._buffer_start = sample_index

    def _to_mono_float(self, raw: bytes):
        np = self._np
        audio = np.frombuffer(raw, dtype="<i2").astype(np.float32) / 32768.0
        if self._config.channels > 1:
            audio = audio.reshape(-1, self._config.channels).mean(axis=1)
        return audio
