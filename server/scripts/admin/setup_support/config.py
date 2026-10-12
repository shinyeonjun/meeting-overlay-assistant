"""setup_server CLI가 공유하는 상수와 실행 시점 설정 묶음."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any


ROLE_CHOICES = ("owner", "admin", "member", "viewer")
DEFAULT_SERVER_HOST = os.getenv("SERVER_HOST", "127.0.0.1")
DEFAULT_SERVER_PORT = int(os.getenv("SERVER_PORT", "8011"))
DEFAULT_LOG_LINES = 18
SETTINGS_PROFILE_ENV_KEY = "SERVER_SETTINGS_PROFILE"
SETTINGS_PRESET_CHOICES = ("cpu-local", "cuda-local", "amd-npu", "api-relay")
SETTINGS_MANAGED_KEYS = (
    "SERVER_HOST",
    "SERVER_PORT",
    "AUTH_ENABLED",
    "LOG_LEVEL",
    "STT_BACKEND",
    "STT_BACKEND_SYSTEM_AUDIO",
    "STT_DEVICE",
    "STT_COMPUTE_TYPE",
    "STT_BASE_URL",
    "STT_MODEL_ID",
    "STT_ENCODER_MODEL_PATH",
    "STT_DECODER_MODEL_PATH",
    "STT_PRELOAD_ON_STARTUP",
    "ANALYZER_BACKEND",
    "RYZEN_AI_INSTALLATION_PATH",
    "SPEAKER_DIARIZER_BACKEND",
    "SPEAKER_DIARIZER_DEVICE",
    "SPEAKER_DIARIZER_WORKER_SCRIPT_PATH",
    "LLM_BASE_URL",
    "REPORT_REFINER_BACKEND",
    SETTINGS_PROFILE_ENV_KEY,
)
SETTINGS_PROFILE_MAP = {
    "cpu-local": {
        "STT_BACKEND": "faster_whisper_streaming",
        "STT_BACKEND_SYSTEM_AUDIO": "hybrid_local_streaming_sherpa",
        "STT_DEVICE": "cpu",
        "STT_COMPUTE_TYPE": "int8",
        "STT_PRELOAD_ON_STARTUP": "true",
        "SPEAKER_DIARIZER_BACKEND": "unknown_speaker",
        "SPEAKER_DIARIZER_DEVICE": "cpu",
        "SPEAKER_DIARIZER_WORKER_SCRIPT_PATH": "server/scripts/workers/pyannote_worker.py",
        "ANALYZER_BACKEND": "insight_pipeline",
        "REPORT_REFINER_BACKEND": "noop",
    },
    "cuda-local": {
        "STT_BACKEND": "faster_whisper_streaming",
        "STT_BACKEND_SYSTEM_AUDIO": "hybrid_local_streaming_sherpa",
        "STT_DEVICE": "cuda",
        "STT_COMPUTE_TYPE": "int8_float16",
        "STT_PRELOAD_ON_STARTUP": "true",
        "SPEAKER_DIARIZER_BACKEND": "unknown_speaker",
        "SPEAKER_DIARIZER_DEVICE": "cpu",
        "SPEAKER_DIARIZER_WORKER_SCRIPT_PATH": "server/scripts/workers/pyannote_worker.py",
        "ANALYZER_BACKEND": "insight_pipeline",
        "REPORT_REFINER_BACKEND": "noop",
    },
    "amd-npu": {
        "STT_BACKEND": "amd_whisper_npu",
        "STT_BACKEND_SYSTEM_AUDIO": "hybrid_local_streaming_sherpa",
        "STT_MODEL_ID": "amd/whisper-small-onnx-npu",
        "STT_DEVICE": "auto",
        "STT_COMPUTE_TYPE": "default",
        "STT_PRELOAD_ON_STARTUP": "true",
        "SPEAKER_DIARIZER_BACKEND": "unknown_speaker",
        "SPEAKER_DIARIZER_DEVICE": "cpu",
        "SPEAKER_DIARIZER_WORKER_SCRIPT_PATH": "server/scripts/workers/pyannote_worker.py",
        "ANALYZER_BACKEND": "insight_pipeline",
        "REPORT_REFINER_BACKEND": "noop",
    },
    "api-relay": {
        "STT_BACKEND": "openai_compatible_audio",
        "STT_BACKEND_SYSTEM_AUDIO": "openai_compatible_audio",
        # 외부 STT API 사용은 프로필 선택으로 명시적으로 허용한다.
        "STT_ALLOW_REMOTE": "true",
        "STT_DEVICE": "auto",
        "STT_COMPUTE_TYPE": "default",
        "STT_PRELOAD_ON_STARTUP": "false",
        "SPEAKER_DIARIZER_BACKEND": "unknown_speaker",
        "SPEAKER_DIARIZER_DEVICE": "cpu",
        "SPEAKER_DIARIZER_WORKER_SCRIPT_PATH": "server/scripts/workers/pyannote_worker.py",
        "ANALYZER_BACKEND": "insight_pipeline",
        "REPORT_REFINER_BACKEND": "noop",
    },
}


@dataclass(frozen=True)
class SetupConfig:
    """명령 한 번의 실행에 필요한 경로와 앱 설정.

    setup_server의 모듈 전역(테스트가 패치하는 이름 포함)을 호출 시점에 읽어 만든다.
    """

    project_root: Path
    app_settings: Any
    env_path: Path
    env_example_path: Path
    profile_dir: Path
