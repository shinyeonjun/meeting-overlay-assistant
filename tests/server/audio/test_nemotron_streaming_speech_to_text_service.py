"""Nemotron streaming 회색 자막 서비스 테스트.

실제 모델 대신, 입력 특징 청크 하나를 받을 때마다 토큰 하나를 내는 가짜 모델과 processor를 쓴다.
"""

from __future__ import annotations

import gc

import numpy as np

from server.app.contexts.live_capture.application.audio.stt.nemotron.model_pool import (
    NemotronModelKey,
    NemotronModelPool,
    NemotronModelSlot,
)
from server.app.contexts.live_capture.application.audio.stt.nemotron.stream_session import (
    LatestTextStreamer,
    NemotronStreamSession,
)
from server.app.contexts.live_capture.application.audio.stt.nemotron_streaming_speech_to_text_service import (
    NemotronStreamingConfig,
    NemotronStreamingSpeechToTextService,
    resolve_nemotron_language,
    resolve_nemotron_model_ref,
)

SR = 16000
CHUNK_SAMPLES = 1600  # 가짜 모델의 입력 청크 = 100ms


class _FakeTokenizer:
    def decode(self, tokens, skip_special_tokens=True):
        return "<ko-KR>" + "".join(chr(0xAC00 + token) for token in tokens)


class _FakeFeatures(dict):
    def __init__(self, frames: int) -> None:
        super().__init__(input_features=np.zeros((1, frames, 1), dtype=np.float32))

    @property
    def input_features(self):
        return self["input_features"]

    def to(self, *args, **kwargs):
        return self


class _FakeFeatureExtractor:
    hop_length = 1
    n_fft = 0


class _FakeProcessor:
    num_samples_first_audio_chunk = CHUNK_SAMPLES
    num_mel_frames_first_audio_chunk = CHUNK_SAMPLES
    num_samples_per_audio_chunk = CHUNK_SAMPLES
    num_mel_frames_per_audio_chunk = CHUNK_SAMPLES
    feature_extractor = _FakeFeatureExtractor()
    tokenizer = _FakeTokenizer()

    def __init__(self) -> None:
        self.languages: list[str] = []

    def __call__(self, audio, *, sampling_rate, is_streaming, is_first_audio_chunk, language, return_tensors):
        self.languages.append(language)
        return _FakeFeatures(len(audio))


class _FakeModel:
    device = "cpu"
    dtype = None

    def __init__(self) -> None:
        self.generate_calls = 0
        self.active = 0
        self.max_active = 0

    def generate(self, *, input_features, streamer, **kwargs):
        self.generate_calls += 1
        self.active += 1
        self.max_active = max(self.max_active, self.active)
        try:
            for index, _ in enumerate(input_features):
                streamer.put(np.array([[index]]))
            streamer.end()
        finally:
            self.active -= 1


def _slot() -> NemotronModelSlot:
    return NemotronModelSlot(model=_FakeModel(), processor=_FakeProcessor())


def _pool() -> NemotronModelPool:
    return NemotronModelPool(
        NemotronModelKey(model_ref="fake", device="cpu", dtype="float32", lookahead_tokens=6),
        loader=lambda key: _slot(),
    )


def _pcm(seconds: float) -> bytes:
    samples = (0.3 * np.ones(int(seconds * SR))).astype(np.float32)
    return (samples * 32767).astype("<i2").tobytes()


def _service(pool: NemotronModelPool, **overrides) -> NemotronStreamingSpeechToTextService:
    return NemotronStreamingSpeechToTextService(
        NemotronStreamingConfig(
            model_ref="fake",
            **overrides,
            partial_emit_interval_ms=100,
            partial_agreement_window=1,
            partial_agreement_min_count=1,
            partial_min_stable_chars=1,
            partial_min_growth_chars=1,
            partial_commit_min_chars_without_boundary=1,
        ),
        pool=pool,
    )


def _wait_text(read, expected_len: int) -> str:
    import time

    # 첫 generate()는 torch를 처음 import하느라 몇 초 걸릴 수 있다.
    deadline = time.monotonic() + 20.0
    while time.monotonic() < deadline:
        text = read()
        if len(text) >= expected_len:
            return text
        time.sleep(0.01)
    return read()


def test_streamer는_언어_태그를_지우고_지금까지의_전체_텍스트를_든다() -> None:
    streamer = LatestTextStreamer(_FakeTokenizer())

    streamer.put(np.array([[0]]))
    streamer.put(np.array([1]))

    assert streamer.text == "가각"


def test_세션은_밀어_넣은_오디오를_청크_단위로_모델에_넘긴다() -> None:
    slot = _slot()
    session = NemotronStreamSession(model=slot.model, processor=slot.processor, language="ko-KR", sample_rate_hz=SR)

    for _ in range(3):
        session.push(np.zeros(CHUNK_SAMPLES, dtype=np.float32))

    assert _wait_text(lambda: session.text, 3) == "가각갂"
    session.close()
    session.join()
    assert session.finished
    assert session.error is None
    assert set(slot.processor.languages) == {"ko-KR"}


def test_세션은_청크가_다_차기_전에는_그_청크를_넘기지_않는다() -> None:
    slot = _slot()
    session = NemotronStreamSession(model=slot.model, processor=slot.processor, language="ko-KR", sample_rate_hz=SR)

    session.push(np.zeros(CHUNK_SAMPLES + CHUNK_SAMPLES // 2, dtype=np.float32))

    assert _wait_text(lambda: session.text, 1) == "가"
    session.close()
    session.join()
    assert session.text == "가"


def test_preview_chunk는_회색_자막을_만든다() -> None:
    pool = _pool()
    service = _service(pool)

    service.preview_chunk(_pcm(0.3))
    _wait_text(lambda: service._lease.session.text, 3)
    results = service.preview_chunk(_pcm(0.1))

    kinds = {result.kind for result in results}
    assert "preview" in kinds
    assert all(result.text.startswith("가") for result in results)


def test_reset_stream은_인식을_끊지_않고_회색_자막만_새로_모은다() -> None:
    pool = _pool()
    service = _service(pool)

    service.preview_chunk(_pcm(0.2))
    _wait_text(lambda: service._lease.session.text, 2)
    service.reset_stream()
    assert service._lease.session.text == ""
    service.preview_chunk(_pcm(0.1))
    second = _wait_text(lambda: service._lease.session.text, 1)

    # 같은 generate()가 이어서 세 번째 청크의 토큰(갂)을 낸다.
    assert second == "갂"
    model = service._lease.slot.model
    assert model.generate_calls == 1
    assert pool.loaded_count == 1


def test_reset_stream_at은_구간_끝_위치_이전_오디오의_토큰을_버린다() -> None:
    pool = _pool()
    service = _service(pool)

    # 청크 3개 → 토큰 가(1600) 각(3200) 갂(4800). 괄호는 토큰이 나온 오디오 끝 위치.
    service.preview_chunk(_pcm(0.3))
    _wait_text(lambda: service._lease.session.text, 3)
    service.reset_stream_at(3200)

    assert service._lease.session.text == "갂"


def test_reset_stream_at은_경계_앞에서_늦게_나온_토큰도_버린다() -> None:
    pool = _pool()
    service = _service(pool)

    service.preview_chunk(_pcm(0.1))
    _wait_text(lambda: service._lease.session.text, 1)
    # 모델이 아직 처리하지 않은 위치(4800)까지가 확정됐다고 먼저 알려 준다.
    service.reset_stream_at(4800)
    service.preview_chunk(_pcm(0.4))
    text = _wait_text(lambda: service._lease.session.text, 2)

    # 3200, 4800 위치 토큰(각, 갂)은 버리고 6400, 8000 위치 토큰(갃, 간)만 남는다.
    assert text == "갃간"


def test_reset_stream_at은_모델_지연만큼_경계를_뒤로_민다() -> None:
    class _LaggingProcessor(_FakeProcessor):
        streaming_latency_ms = 100  # 1600샘플

    pool = NemotronModelPool(
        NemotronModelKey(model_ref="fake", device="cpu", dtype="float32", lookahead_tokens=6),
        loader=lambda key: NemotronModelSlot(model=_FakeModel(), processor=_LaggingProcessor()),
    )
    service = _service(pool)

    service.preview_chunk(_pcm(0.3))
    _wait_text(lambda: service._lease.session.text, 3)
    service.reset_stream_at(1600)

    # 경계 1600 + 지연 1600 = 3200 이하 위치 토큰(가, 각)을 버린다.
    assert service._lease.session.text == "갂"


def test_닫을_때_generate가_안_끝나면_그_모델은_풀에_돌려주지_않는다() -> None:
    import threading

    release = threading.Event()

    class _StuckModel(_FakeModel):
        def generate(self, *, input_features, streamer, **kwargs):
            next(iter(input_features))
            release.wait(5)

    pool = NemotronModelPool(
        NemotronModelKey(model_ref="fake", device="cpu", dtype="float32", lookahead_tokens=6),
        loader=lambda key: NemotronModelSlot(model=_StuckModel(), processor=_FakeProcessor()),
    )
    service = _service(pool, join_timeout_seconds=0.05)
    service.preview_chunk(_pcm(0.1))

    service.close()

    assert pool.idle_count == 0
    release.set()


def test_인식_세션이_오류로_끝나면_다음_청크에서_새로_연다() -> None:
    class _BrokenOnceModel(_FakeModel):
        def generate(self, **kwargs):
            if self.generate_calls == 0:
                self.generate_calls += 1
                raise RuntimeError("boom")
            return super().generate(**kwargs)

    pool = NemotronModelPool(
        NemotronModelKey(model_ref="fake", device="cpu", dtype="float32", lookahead_tokens=6),
        loader=lambda key: NemotronModelSlot(model=_BrokenOnceModel(), processor=_FakeProcessor()),
    )
    service = _service(pool)
    service.preview_chunk(_pcm(0.1))
    first_session = service._lease.session
    first_session.join()
    assert first_session.error is not None

    service.preview_chunk(_pcm(0.1))

    assert service._lease.session is not first_session
    assert _wait_text(lambda: service._lease.session.text, 1) == "가"


def test_서비스가_사라지면_모델을_풀에_돌려준다() -> None:
    pool = _pool()
    service = _service(pool)
    service.preview_chunk(_pcm(0.1))
    assert pool.idle_count == 0

    del service
    gc.collect()

    assert pool.idle_count == 1
    second = _service(pool)
    second.preview_chunk(_pcm(0.1))
    assert pool.loaded_count == 1


def test_동시에_쓰는_서비스는_모델을_따로_빌린다() -> None:
    pool = _pool()
    first, second = _service(pool), _service(pool)

    first.preview_chunk(_pcm(0.1))
    second.preview_chunk(_pcm(0.1))

    assert pool.loaded_count == 2
    assert first._lease.slot is not second._lease.slot


def test_preload는_모델을_예열하고_풀에_둔다() -> None:
    pool = _pool()

    _service(pool).preload()

    assert pool.loaded_count == 1
    assert pool.idle_count == 1


def test_언어_코드는_locale로_바꾼다() -> None:
    assert resolve_nemotron_language("ko") == "ko-KR"
    assert resolve_nemotron_language(None) == "ko-KR"
    assert resolve_nemotron_language("ja-JP") == "ja-JP"


def test_config_json이_있는_폴더만_로컬_모델로_쓴다(tmp_path) -> None:
    whisper_dir = tmp_path / "whisper"
    whisper_dir.mkdir()
    local_dir = tmp_path / "nemotron"
    local_dir.mkdir()
    (local_dir / "config.json").write_text("{}", encoding="utf-8")

    assert resolve_nemotron_model_ref(model_id="nvidia/x", model_path=str(whisper_dir)) == "nvidia/x"
    assert resolve_nemotron_model_ref(model_id="nvidia/x", model_path=None) == "nvidia/x"
    assert resolve_nemotron_model_ref(model_id="nvidia/x", model_path=str(local_dir)) == str(local_dir.resolve())
