"""화자 분리기 생성 팩토리."""

from __future__ import annotations

from collections.abc import Callable

from server.app.services.diarization.pyannote_speaker_diarizer import (
    PyannoteDiarizerConfig,
    PyannoteSpeakerDiarizer,
)
from server.app.services.diarization.pyannote_worker_speaker_diarizer import (
    PyannoteWorkerConfig,
    PyannoteWorkerSpeakerDiarizer,
)
from server.app.services.diarization.speaker_diarizer import SpeakerDiarizer
from server.app.services.diarization.unknown_speaker_diarizer import (
    UnknownSpeakerDiarizer,
    UnknownSpeakerDiarizerConfig,
)


def create_speaker_diarizer(
    backend_name: str,
    *,
    model_id: str,
    auth_token: str | None = None,
    device: str = "cpu",
    default_speaker_label: str = "화자-미분류",
    worker_python_executable: str | None = None,
    worker_script_path: str | None = None,
    worker_timeout_seconds: float = 120.0,
) -> SpeakerDiarizer:
    """설정에 맞는 화자 분리기를 생성한다."""

    builders: dict[str, Callable[[], SpeakerDiarizer]] = {
        "unknown_speaker": lambda: UnknownSpeakerDiarizer(
            UnknownSpeakerDiarizerConfig(
                speaker_label=default_speaker_label,
            )
        ),
        "pyannote": lambda: PyannoteSpeakerDiarizer(
            PyannoteDiarizerConfig(
                model_id=model_id,
                auth_token=auth_token,
                device=device,
            )
        ),
        "pyannote_worker": lambda: PyannoteWorkerSpeakerDiarizer(
            PyannoteWorkerConfig(
                python_executable=worker_python_executable or "python",
                script_path=worker_script_path or "server/scripts/workers/pyannote_worker.py",
                model_id=model_id,
                auth_token=auth_token,
                device=device,
                timeout_seconds=worker_timeout_seconds,
            )
        ),
    }
    builder = builders.get(backend_name)
    if builder is None:
        raise ValueError(f"지원하지 않는 speaker diarizer backend입니다: {backend_name}")
    return builder()
