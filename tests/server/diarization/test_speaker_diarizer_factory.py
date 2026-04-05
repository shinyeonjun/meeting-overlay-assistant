"""화자 분리기 팩토리 테스트."""

import pytest

from server.app.services.diarization.pyannote_speaker_diarizer import PyannoteSpeakerDiarizer
from server.app.services.diarization.pyannote_worker_speaker_diarizer import (
    PyannoteWorkerSpeakerDiarizer,
)
from server.app.services.diarization.speaker_diarizer_factory import create_speaker_diarizer
from server.app.services.diarization.unknown_speaker_diarizer import UnknownSpeakerDiarizer


class TestSpeakerDiarizerFactory:
    """화자 분리기 생성 로직을 검증한다."""

    def test_unknown_speaker_backend를_선택하면_placeholder_분리기를_반환한다(self):
        diarizer = create_speaker_diarizer(
            "unknown_speaker",
            model_id="pyannote/speaker-diarization-community-1",
        )

        assert isinstance(diarizer, UnknownSpeakerDiarizer)

    def test_pyannote_backend를_선택하면_pyannote_분리기를_반환한다(self):
        diarizer = create_speaker_diarizer(
            "pyannote",
            model_id="pyannote/speaker-diarization-community-1",
        )

        assert isinstance(diarizer, PyannoteSpeakerDiarizer)

    def test_pyannote_worker_backend를_선택하면_worker_분리기를_반환한다(self):
        diarizer = create_speaker_diarizer(
            "pyannote_worker",
            model_id="pyannote/speaker-diarization-community-1",
            auth_token="hf_test",
            worker_python_executable="D:/caps/venvs/diarization/Scripts/python.exe",
            worker_script_path="D:/caps/server/scripts/workers/pyannote_worker.py",
        )

        assert isinstance(diarizer, PyannoteWorkerSpeakerDiarizer)

    def test_지원하지_않는_backend를_선택하면_예외가_발생한다(self):
        with pytest.raises(ValueError):
            create_speaker_diarizer("unknown", model_id="x")
