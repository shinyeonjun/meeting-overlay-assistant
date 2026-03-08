"""전처리를 수행하지 않는 기본 오디오 전처리기."""

from __future__ import annotations

from backend.app.services.audio.preprocessing.audio_preprocessing import AudioBuffer


class BypassAudioPreprocessor:
    """입력 오디오를 그대로 통과시키는 기본 구현."""

    def preprocess(self, audio: AudioBuffer) -> AudioBuffer:
        return audio

