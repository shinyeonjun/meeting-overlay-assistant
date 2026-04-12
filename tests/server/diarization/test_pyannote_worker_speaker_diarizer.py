"""화자 분리 영역의 test pyannote worker speaker diarizer 동작을 검증한다."""
from __future__ import annotations

from dataclasses import replace
import json
import subprocess

import pytest

from server.app.services.audio.preprocessing.audio_preprocessing import AudioBuffer
from server.app.services.diarization.pyannote_worker_speaker_diarizer import (
    PyannoteWorkerConfig,
    PyannoteWorkerSpeakerDiarizer,
)


@pytest.fixture
def sample_audio_buffer() -> AudioBuffer:
    """sample audio buffer 동작을 검증한다."""
    return AudioBuffer(
        sample_rate_hz=16000,
        sample_width_bytes=2,
        channels=1,
        raw_bytes=(b"\x00\x00" * 1600),
    )


@pytest.fixture
def worker_config() -> PyannoteWorkerConfig:
    """worker config 동작을 검증한다."""
    return PyannoteWorkerConfig(
        python_executable="D:/caps/venvs/diarization/Scripts/python.exe",
        script_path="D:/caps/server/scripts/workers/pyannote_worker.py",
        model_id="pyannote/speaker-diarization-community-1",
        auth_token="hf_test",
        device="cpu",
        timeout_seconds=30.0,
    )


class TestPyannoteWorkerSpeakerDiarizer:
    """PyannoteWorkerSpeakerDiarizer 동작을 검증한다."""
    def test_worker_json을_세그먼트로_변환한다(
        self,
        monkeypatch: pytest.MonkeyPatch,
        sample_audio_buffer: AudioBuffer,
        worker_config: PyannoteWorkerConfig,
    ) -> None:
        diarizer = PyannoteWorkerSpeakerDiarizer(worker_config)
        payload = {
            "segments": [
                {"speaker_label": "SPEAKER_00", "start_ms": 0, "end_ms": 1200},
                {"speaker_label": "SPEAKER_01", "start_ms": 1200, "end_ms": 2500},
            ]
        }

        def fake_run(*args, **kwargs):  # noqa: ANN002, ANN003
            return subprocess.CompletedProcess(
                args=args[0],
                returncode=0,
                stdout=json.dumps(payload, ensure_ascii=False),
                stderr="",
            )

        monkeypatch.setattr(subprocess, "run", fake_run)

        segments = diarizer.diarize(sample_audio_buffer)

        assert len(segments) == 2
        assert segments[0].speaker_label == "SPEAKER_00"
        assert segments[1].start_ms == 1200

    def test_worker_실패시_runtime_error를_발생한다(
        self,
        monkeypatch: pytest.MonkeyPatch,
        sample_audio_buffer: AudioBuffer,
        worker_config: PyannoteWorkerConfig,
    ) -> None:
        diarizer = PyannoteWorkerSpeakerDiarizer(worker_config)

        def fake_run(*args, **kwargs):  # noqa: ANN002, ANN003
            return subprocess.CompletedProcess(
                args=args[0],
                returncode=1,
                stdout="",
                stderr="worker failed",
            )

        monkeypatch.setattr(subprocess, "run", fake_run)

        with pytest.raises(RuntimeError, match="pyannote worker 실행에 실패했습니다"):
            diarizer.diarize(sample_audio_buffer)

    def test_worker_timeout시_설명있는_runtime_error를_발생한다(
        self,
        monkeypatch: pytest.MonkeyPatch,
        sample_audio_buffer: AudioBuffer,
        worker_config: PyannoteWorkerConfig,
    ) -> None:
        diarizer = PyannoteWorkerSpeakerDiarizer(worker_config)

        def fake_run(*args, **kwargs):  # noqa: ANN002, ANN003
            raise subprocess.TimeoutExpired(cmd=args[0], timeout=kwargs["timeout"])

        monkeypatch.setattr(subprocess, "run", fake_run)

        with pytest.raises(RuntimeError, match="시간 초과"):
            diarizer.diarize(sample_audio_buffer)

    def test_토큰이_없으면_즉시_실패한다(
        self,
        sample_audio_buffer: AudioBuffer,
        worker_config: PyannoteWorkerConfig,
    ) -> None:
        diarizer = PyannoteWorkerSpeakerDiarizer(replace(worker_config, auth_token=None))

        with pytest.raises(RuntimeError, match="Hugging Face 토큰"):
            diarizer.diarize(sample_audio_buffer)

