"""오디오 후처리 서비스 테스트."""

from __future__ import annotations

import wave
from pathlib import Path

from server.app.services.audio.preprocessing.bypass_audio_preprocessor import BypassAudioPreprocessor
from server.app.services.audio.stt.transcription import TranscriptionResult
from server.app.services.audio.filters.transcription_guard import TranscriptionGuard, TranscriptionGuardConfig
from server.app.services.diarization.unknown_speaker_diarizer import (
    UnknownSpeakerDiarizer,
    UnknownSpeakerDiarizerConfig,
)
from server.app.services.reports.audio.audio_postprocessing_service import (
    AudioPostprocessingService,
)


class _FakeSpeechToTextService:
    def transcribe(self, segment):  # noqa: ANN001
        return TranscriptionResult(text="테스트 발화", confidence=0.95)


class TestAudioPostprocessingService:
    """WAV 기반 후처리 파이프라인을 검증한다."""

    def test_wav를_읽어_화자별_전사_목록을_만든다(self, tmp_path: Path):
        wav_path = tmp_path / "sample.wav"
        _write_pcm_wave(wav_path)

        service = AudioPostprocessingService(
            audio_preprocessor=BypassAudioPreprocessor(),
            speaker_diarizer=UnknownSpeakerDiarizer(
                UnknownSpeakerDiarizerConfig(speaker_label="화자-A")
            ),
            speech_to_text_service=_FakeSpeechToTextService(),
            transcription_guard=TranscriptionGuard(
                TranscriptionGuardConfig(
                    min_confidence=0.1,
                    short_text_min_confidence=0.1,
                    boundary_terms=(),
                )
            ),
            expected_sample_rate_hz=16000,
            expected_sample_width_bytes=2,
            expected_channels=1,
        )

        segments = service.build_speaker_transcript(wav_path)

        assert len(segments) == 1
        assert segments[0].speaker_label == "화자-A"
        assert segments[0].text == "테스트 발화"


def _write_pcm_wave(path: Path) -> None:
    raw_bytes = b"\x00\x00" * 16000
    with wave.open(str(path), "wb") as wav_file:
        wav_file.setnchannels(1)
        wav_file.setsampwidth(2)
        wav_file.setframerate(16000)
        wav_file.writeframes(raw_bytes)


