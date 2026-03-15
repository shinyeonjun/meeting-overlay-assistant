"""오디오 전처리 팩토리 테스트."""

import pytest

from server.app.services.audio.preprocessing.audio_preprocessor_factory import create_audio_preprocessor
from server.app.services.audio.preprocessing.bypass_audio_preprocessor import BypassAudioPreprocessor
from server.app.services.audio.preprocessing.deepfilternet_audio_preprocessor import (
    DeepFilterNetAudioPreprocessor,
)


class TestAudioPreprocessorFactory:
    """오디오 전처리기 생성 로직을 검증한다."""

    def test_bypass_backend를_선택하면_bypass_preprocessor를_반환한다(self):
        preprocessor = create_audio_preprocessor("bypass")

        assert isinstance(preprocessor, BypassAudioPreprocessor)

    def test_deepfilternet_backend를_선택하면_deepfilternet_preprocessor를_반환한다(self):
        preprocessor = create_audio_preprocessor("deepfilternet")

        assert isinstance(preprocessor, DeepFilterNetAudioPreprocessor)

    def test_지원하지_않는_backend를_선택하면_예외가_발생한다(self):
        with pytest.raises(ValueError):
            create_audio_preprocessor("unknown")

