"""밀어 넣는(push) 오디오를 Nemotron의 당겨 가는(pull) streaming generate()에 잇는 세션.

transformers의 Nemotron streaming은 generate()가 입력 특징 generator를 끝까지 당겨 가며 토큰을 낸다.
우리 서비스는 preview_chunk()로 오디오를 조금씩 밀어 넣으므로, generate()를 전용 스레드에서 돌리고
generator가 필요한 만큼 오디오가 쌓일 때까지 기다리게 한다.
"""

from __future__ import annotations

from contextlib import nullcontext
import logging
import re
from threading import Condition, Lock, Thread
from typing import Any, Callable

import numpy as np

logger = logging.getLogger(__name__)

_LANGUAGE_TAG = re.compile(r"<[a-z]{2}-[A-Z]{2}>")


def strip_language_tags(text: str) -> str:
    """모델이 앞에 붙이는 언어 태그(<ko-KR>)를 지운다."""

    return _LANGUAGE_TAG.sub("", text).strip()


class LatestTextStreamer:
    """받은 토큰 전체를 매번 다시 decode해 '지금까지의 전체 텍스트'를 들고 있는다.

    transformers TextStreamer는 띄어쓰기 전까지 글자를 붙잡아 두므로 회색 자막에는 늦다.
    토큰마다 그 토큰이 나올 때 모델이 받아 간 오디오 끝 위치(샘플)를 함께 기록해,
    확정 경계보다 앞선 오디오에서 나온 토큰을 골라 버릴 수 있게 한다.
    """

    def __init__(self, tokenizer: Any, *, position: Callable[[], int] | None = None) -> None:
        self._tokenizer = tokenizer
        self._position = position or (lambda: 0)
        self._tokens: list[tuple[int, int]] = []  # (token, 오디오 끝 위치)
        self._text = ""
        self._boundary = -1
        self._lock = Lock()

    def put(self, value) -> None:
        tokens = value.tolist() if hasattr(value, "tolist") else list(value)
        while tokens and isinstance(tokens[0], list):
            tokens = tokens[0]
        if not tokens:
            return
        position = self._position()
        with self._lock:
            if position <= self._boundary:
                return  # 경계 앞 오디오(이미 확정된 구간)에서 늦게 나온 토큰
            self._tokens.extend((int(token), position) for token in tokens)
            self._refresh()

    def end(self) -> None:
        return None

    def mark(self, boundary: int | None = None) -> None:
        """boundary(샘플) 이하 오디오에서 나온 토큰을 버린다. 없으면 지금까지 받은 토큰을 모두 버린다."""

        with self._lock:
            self._boundary = max(self._boundary, self._position() if boundary is None else boundary)
            self._tokens = [item for item in self._tokens if item[1] > self._boundary]
            self._refresh()

    def _refresh(self) -> None:
        if not self._tokens:
            self._text = ""
            return
        text = self._tokenizer.decode([token for token, _ in self._tokens], skip_special_tokens=True)
        self._text = strip_language_tags(text)

    @property
    def text(self) -> str:
        with self._lock:
            return self._text


class NemotronStreamSession:
    """한 발화 묶음(리셋 사이)의 streaming 인식 세션. 모델 슬롯 하나를 독점한다."""

    def __init__(
        self,
        *,
        model: Any,
        processor: Any,
        language: str,
        sample_rate_hz: int,
        join_timeout_seconds: float = 5.0,
    ) -> None:
        self._model = model
        self._processor = processor
        self._language = language
        self._sample_rate_hz = sample_rate_hz
        self._join_timeout_seconds = join_timeout_seconds
        self._consumed_end = 0  # 모델에 넘긴 마지막 청크의 끝 위치(샘플)
        latency_ms = getattr(processor, "streaming_latency_ms", 0) or 0
        self._latency_samples = int(sample_rate_hz * latency_ms / 1000)
        self._streamer = LatestTextStreamer(processor.tokenizer, position=lambda: self._consumed_end)
        self._buffer = np.zeros(0, dtype=np.float32)
        self._buffer_start = 0  # _buffer[0]의 절대 샘플 위치
        self._closed = False
        self._condition = Condition()
        self._thread: Thread | None = None
        self.error: BaseException | None = None

    @property
    def text(self) -> str:
        return self._streamer.text

    def push(self, samples: np.ndarray) -> None:
        if samples.size == 0:
            return
        with self._condition:
            if self._closed:
                return
            self._buffer = np.concatenate([self._buffer, samples.astype(np.float32, copy=False)])
            self._condition.notify_all()
            if self._thread is None:
                self._thread = Thread(target=self._run, name="nemotron-stream", daemon=True)
                self._thread.start()

    def close(self) -> None:
        """입력을 끝낸다. generate()는 남은 청크를 처리하고 스스로 끝난다."""

        with self._condition:
            self._closed = True
            self._condition.notify_all()

    def join(self) -> bool:
        """generate() 스레드가 끝날 때까지 기다린다. 제한 시간 안에 끝났으면 True.

        False면 모델이 아직 generate() 중이므로 그 모델을 다른 세션에 주면 안 된다.
        """

        thread = self._thread
        if thread is None:
            return True
        thread.join(self._join_timeout_seconds)
        if thread.is_alive():
            logger.warning("Nemotron stream 스레드가 %.1f초 안에 끝나지 않았습니다.", self._join_timeout_seconds)
            return False
        return True

    def mark(self, boundary: int | None = None) -> None:
        """인식은 그대로 이어 가고, text는 boundary(세션 기준 샘플) 뒤 오디오에서 나온 것만 남긴다.

        토큰에는 '그 토큰이 나올 때 모델이 받아 간 오디오 끝'을 기록하는데, 모델은 lookahead만큼
        뒤 오디오를 보고서야 앞 오디오의 토큰을 낸다. 그래서 경계 직전 말의 토큰은 경계 뒤
        streaming_latency_ms(lookahead 6이면 560ms) 안쪽 위치로 기록된다. 그만큼 경계를 뒤로 민다.
        다음 말은 쉼(최소 300ms) 뒤에 시작하고 그 토큰도 lookahead만큼 늦게 기록되므로 잘리지 않는다.
        boundary가 없으면 지금까지 모델에 넘긴 오디오까지를 경계로 본다.
        """

        if boundary is not None:
            boundary += self._latency_samples
        self._streamer.mark(boundary)

    @property
    def finished(self) -> bool:
        return self._thread is None or not self._thread.is_alive()

    @property
    def usable(self) -> bool:
        """입력을 더 받을 수 있는지. generate() 스레드가 오류로 끝났으면 False."""

        with self._condition:
            if self._closed:
                return False
        return self._thread is None or self._thread.is_alive()

    def _wait_for_samples(self, start: int, end: int) -> np.ndarray | None:
        """절대 위치 [start, end) 오디오가 다 들어올 때까지 기다린다. 입력이 끝나면 None."""

        with self._condition:
            while self._buffer_start + self._buffer.size < end and not self._closed:
                self._condition.wait()
            if self._buffer_start + self._buffer.size < end:
                return None
            # start 이전 오디오는 다시 쓰지 않으므로 버린다.
            drop = max(start - self._buffer_start, 0)
            if drop:
                self._buffer = self._buffer[drop:]
                self._buffer_start += drop
            offset = start - self._buffer_start
            return self._buffer[offset : offset + (end - start)].copy()

    def _features(self, audio: np.ndarray, *, first: bool):
        inputs = self._processor(
            audio,
            sampling_rate=self._sample_rate_hz,
            is_streaming=True,
            is_first_audio_chunk=first,
            language=self._language,
            return_tensors="pt",
        )
        return inputs.to(self._model.device, dtype=self._model.dtype)

    def _run(self) -> None:
        try:
            self._generate()
        except BaseException as error:  # noqa: BLE001 - 스레드 밖으로 알릴 길이 없어 기록만 한다.
            self.error = error
            logger.exception("Nemotron streaming generate 실패")

    def _generate(self) -> None:
        processor = self._processor
        first_audio = self._wait_for_samples(0, processor.num_samples_first_audio_chunk)
        if first_audio is None:
            return
        first = self._features(first_audio, first=True)
        self._consumed_end = processor.num_samples_first_audio_chunk
        hop = processor.feature_extractor.hop_length
        n_fft = processor.feature_extractor.n_fft

        def feature_chunks():
            yield first.input_features[:, : processor.num_mel_frames_first_audio_chunk, :]
            mel_index = processor.num_mel_frames_first_audio_chunk
            while True:
                start = mel_index * hop - n_fft // 2
                end = start + processor.num_samples_per_audio_chunk
                audio = self._wait_for_samples(start, end)
                if audio is None:
                    return
                features = self._features(audio, first=False).input_features
                self._consumed_end = end
                yield features
                mel_index += processor.num_mel_frames_per_audio_chunk

        with _inference_mode():
            self._model.generate(**{**first, "input_features": feature_chunks(), "streamer": self._streamer})


def _inference_mode():
    try:
        import torch
    except ImportError:  # torch 없는 환경(가짜 모델 테스트)
        return nullcontext()
    return torch.inference_mode()
