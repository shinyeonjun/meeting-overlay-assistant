"""pyannote 화자 분리기 테스트."""

from __future__ import annotations

import builtins
from dataclasses import dataclass

import pytest

from server.app.services.audio.preprocessing.audio_preprocessing import AudioBuffer
from server.app.services.diarization.pyannote_speaker_diarizer import (
    PyannoteDiarizerConfig,
    PyannoteSpeakerDiarizer,
)


@dataclass(frozen=True)
class _FakeTurn:
    start: float
    end: float


class _FakeDiarizationResult:
    def itertracks(self, yield_label: bool = False):
        if not yield_label:
            return []
        return [
            (_FakeTurn(0.0, 1.2), None, "SPEAKER_00"),
            (_FakeTurn(1.2, 2.4), None, "SPEAKER_01"),
        ]


class _FakePipeline:
    def __init__(self) -> None:
        self.loaded_input = None
        self.device_name: str | None = None

    def __call__(self, audio_input):
        self.loaded_input = audio_input
        return _FakeDiarizationResult()

    def to(self, device) -> None:  # noqa: ANN001
        self.device_name = str(device)


class _FakeTensor:
    def __init__(self, shape: tuple[int, ...]) -> None:
        self.shape = shape

    def __truediv__(self, other):  # noqa: ANN001
        return self

    def reshape(self, *shape: int):
        return _FakeTensor(shape)

    def transpose(self, dim0: int, dim1: int):  # noqa: ANN001
        shape = list(self.shape)
        shape[dim0], shape[dim1] = shape[dim1], shape[dim0]
        return _FakeTensor(tuple(shape))

    def unsqueeze(self, dim: int):  # noqa: ANN001
        shape = list(self.shape)
        shape.insert(dim, 1)
        return _FakeTensor(tuple(shape))


class _FakeTorch:
    float32 = "float32"

    @staticmethod
    def tensor(values, dtype=None):  # noqa: ANN001
        return _FakeTensor((len(values),))

    @staticmethod
    def device(name: str) -> str:
        return name


class TestPyannoteSpeakerDiarizer:
    """pyannote 화자 분리기 동작을 검증한다."""

    def test_토큰이_없으면_예외가_발생한다(self):
        diarizer = PyannoteSpeakerDiarizer(
            PyannoteDiarizerConfig(
                model_id="pyannote/speaker-diarization-community-1",
                auth_token=None,
            )
        )

        with pytest.raises(RuntimeError):
            diarizer.diarize(_make_audio())

    def test_화자_구간을_speaker_segment로_변환한다(self, monkeypatch):
        fake_pipeline = _FakePipeline()
        diarizer = PyannoteSpeakerDiarizer(
            PyannoteDiarizerConfig(
                model_id="pyannote/speaker-diarization-community-1",
                auth_token="token",
            )
        )
        monkeypatch.setattr(diarizer, "_build_pipeline", lambda: fake_pipeline)
        monkeypatch.setattr("builtins.__import__", _fake_import)

        segments = diarizer.diarize(_make_audio())

        assert len(segments) == 2
        assert segments[0].speaker_label == "SPEAKER_00"
        assert segments[0].start_ms == 0
        assert segments[0].end_ms == 1200
        assert segments[1].speaker_label == "SPEAKER_01"
        assert "waveform" in fake_pipeline.loaded_input
        assert fake_pipeline.loaded_input["sample_rate"] == 16000

    def test_gpu_장치가_설정되면_pipeline_to를_호출한다(self, monkeypatch):
        fake_pipeline = _FakePipeline()
        diarizer = PyannoteSpeakerDiarizer(
            PyannoteDiarizerConfig(
                model_id="pyannote/speaker-diarization-community-1",
                auth_token="token",
                device="cuda",
            )
        )

        monkeypatch.setattr("builtins.__import__", _fake_import)
        diarizer._move_pipeline_to_device(fake_pipeline)

        assert fake_pipeline.device_name == "cuda"

    def test_waveform_input을_직접_구성한다(self, monkeypatch):
        diarizer = PyannoteSpeakerDiarizer(
            PyannoteDiarizerConfig(
                model_id="pyannote/speaker-diarization-community-1",
                auth_token="token",
            )
        )
        monkeypatch.setattr("builtins.__import__", _fake_import)

        waveform_input = diarizer._build_waveform_input(_make_audio())

        assert waveform_input["sample_rate"] == 16000
        assert tuple(waveform_input["waveform"].shape) == (1, 16000)


_ORIGINAL_IMPORT = builtins.__import__


def _fake_import(name, *args, **kwargs):  # noqa: ANN001, ANN002, ANN003
    if name == "torch":
        return _FakeTorch
    return _ORIGINAL_IMPORT(name, *args, **kwargs)


def _make_audio() -> AudioBuffer:
    return AudioBuffer(
        sample_rate_hz=16000,
        sample_width_bytes=2,
        channels=1,
        raw_bytes=b"\x00\x00" * 16000,
    )

