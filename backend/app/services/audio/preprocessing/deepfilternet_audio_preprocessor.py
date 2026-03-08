"""DeepFilterNet 기반 오디오 전처리기 스캐폴드."""

from __future__ import annotations

from dataclasses import dataclass

from backend.app.services.audio.preprocessing.audio_preprocessing import AudioBuffer


@dataclass(frozen=True)
class DeepFilterNetConfig:
    """DeepFilterNet 전처리 설정."""

    model_path: str | None = None
    atten_lim_db: float = 18.0


class DeepFilterNetAudioPreprocessor:
    """DeepFilterNet 의존성이 준비됐을 때 사용할 전처리기."""

    def __init__(self, config: DeepFilterNetConfig) -> None:
        self._config = config

    def preprocess(self, audio: AudioBuffer) -> AudioBuffer:
        try:
            __import__("df")
        except ImportError as exc:
            raise RuntimeError(
                "DeepFilterNet 전처리기는 아직 설치되지 않았습니다. "
                "추후 `pip install deepfilternet` 또는 프로젝트 전용 설치 스크립트로 연결하세요."
            ) from exc

        raise NotImplementedError(
            "DeepFilterNet 전처리기는 스캐폴드만 추가된 상태입니다. "
            "모델 로딩과 PCM 입출력 연결을 다음 단계에서 구현하세요."
        )

