"""별도 worker 프로세스로 pyannote diarization을 호출하는 구현."""

from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
import subprocess
import tempfile
import wave

from backend.app.services.audio.preprocessing.audio_preprocessing import AudioBuffer
from backend.app.services.diarization.speaker_diarizer import SpeakerSegment


@dataclass(frozen=True)
class PyannoteWorkerConfig:
    """외부 diarization worker 호출 설정."""

    python_executable: str
    script_path: str
    model_id: str
    auth_token: str | None = None
    device: str = "cpu"
    timeout_seconds: float = 120.0


class PyannoteWorkerSpeakerDiarizer:
    """별도 Python 환경의 pyannote worker를 subprocess로 실행한다."""

    def __init__(self, config: PyannoteWorkerConfig) -> None:
        self._config = config

    def diarize(self, audio: AudioBuffer) -> list[SpeakerSegment]:
        if not audio.raw_bytes:
            return []
        if not self._config.auth_token:
            raise RuntimeError(
                "pyannote worker를 사용하려면 Hugging Face 토큰이 필요합니다. "
                "`.env`의 `SPEAKER_DIARIZER_AUTH_TOKEN` 또는 `HF_TOKEN`을 설정하세요."
            )

        temp_audio_path = self._write_temp_wave_file(audio)
        try:
            payload = self._run_worker(temp_audio_path)
        finally:
            temp_audio_path.unlink(missing_ok=True)

        return [
            SpeakerSegment(
                speaker_label=str(item["speaker_label"]),
                start_ms=int(item["start_ms"]),
                end_ms=int(item["end_ms"]),
            )
            for item in payload["segments"]
        ]

    def _run_worker(self, audio_path: Path) -> dict[str, object]:
        command = [
            self._config.python_executable,
            self._config.script_path,
            "--audio-path",
            str(audio_path),
            "--model-id",
            self._config.model_id,
            "--device",
            self._config.device,
            "--auth-token",
            self._config.auth_token or "",
        ]
        completed = subprocess.run(
            command,
            capture_output=True,
            text=True,
            encoding="utf-8",
            timeout=self._config.timeout_seconds,
            check=False,
        )
        if completed.returncode != 0:
            stderr_text = completed.stderr.strip() or completed.stdout.strip()
            raise RuntimeError(
                "pyannote worker 실행에 실패했습니다. "
                f"returncode={completed.returncode} stderr={stderr_text}"
            )

        try:
            return json.loads(completed.stdout)
        except json.JSONDecodeError as exc:
            raise RuntimeError(
                "pyannote worker가 올바른 JSON을 반환하지 않았습니다. "
                f"stdout={completed.stdout!r}"
            ) from exc

    @staticmethod
    def _write_temp_wave_file(audio: AudioBuffer) -> Path:
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as temp_file:
            temp_path = Path(temp_file.name)
        with wave.open(str(temp_path), "wb") as wav_file:
            wav_file.setnchannels(audio.channels)
            wav_file.setsampwidth(audio.sample_width_bytes)
            wav_file.setframerate(audio.sample_rate_hz)
            wav_file.writeframes(audio.raw_bytes)
        return temp_path

