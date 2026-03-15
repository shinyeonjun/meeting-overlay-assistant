"""오디오 전처리기 생성 팩토리."""

from __future__ import annotations

from collections.abc import Callable

from server.app.services.audio.preprocessing.audio_preprocessing import AudioPreprocessor
from server.app.services.audio.preprocessing.bypass_audio_preprocessor import BypassAudioPreprocessor
from server.app.services.audio.preprocessing.deepfilternet_audio_preprocessor import (
    DeepFilterNetAudioPreprocessor,
    DeepFilterNetConfig,
)


def create_audio_preprocessor(
    backend_name: str,
    *,
    model_path: str | None = None,
    atten_lim_db: float = 18.0,
) -> AudioPreprocessor:
    """설정에 맞는 오디오 전처리기를 생성한다."""

    builders: dict[str, Callable[[], AudioPreprocessor]] = {
        "bypass": BypassAudioPreprocessor,
        "deepfilternet": lambda: DeepFilterNetAudioPreprocessor(
            DeepFilterNetConfig(
                model_path=model_path,
                atten_lim_db=atten_lim_db,
            )
        ),
    }
    builder = builders.get(backend_name)
    if builder is None:
        raise ValueError(f"지원하지 않는 audio preprocessor backend입니다: {backend_name}")
    return builder()

