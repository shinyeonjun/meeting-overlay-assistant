"""오디오 영역의 test audio postprocessing service 동작을 검증한다."""
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
from server.app.services.diarization.speaker_diarizer import SpeakerSegment
from server.app.services.reports.audio.audio_postprocessing_service import (
    AudioPostprocessingService,
)


class _FakeSpeechToTextService:
    def __init__(self) -> None:
        self.calls: list[tuple[int, int]] = []

    def transcribe(self, segment):  # noqa: ANN001
        self.calls.append((segment.start_ms, segment.end_ms))
        return TranscriptionResult(text="테스트 발화", confidence=0.95)


class _FakeSpeakerDiarizer:
    def __init__(self, segments: list[SpeakerSegment]) -> None:
        self._segments = segments

    def diarize(self, audio):  # noqa: ANN001
        del audio
        return list(self._segments)


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

    def test_같은_화자_인접_구간은_병합하고_너무_짧은_조각은_건너뛴다(self, tmp_path: Path):
        wav_path = tmp_path / "sample.wav"
        _write_pcm_wave(wav_path)
        speech_to_text_service = _FakeSpeechToTextService()

        service = AudioPostprocessingService(
            audio_preprocessor=BypassAudioPreprocessor(),
            speaker_diarizer=_FakeSpeakerDiarizer(
                [
                    SpeakerSegment("화자-A", 0, 80),
                    SpeakerSegment("화자-A", 120, 260),
                    SpeakerSegment("화자-A", 320, 360),
                    SpeakerSegment("화자-B", 600, 760),
                ]
            ),
            speech_to_text_service=speech_to_text_service,
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

        assert [(item.speaker_label, item.start_ms, item.end_ms) for item in segments] == [
            ("화자-A", 0, 360),
            ("화자-B", 600, 760),
        ]
        assert speech_to_text_service.calls == [(0, 360), (600, 760)]

    def test_segment_callback으로_전사_진행상황을_받을_수_있다(self, tmp_path: Path):
        wav_path = tmp_path / "sample.wav"
        _write_pcm_wave(wav_path)
        callback_segments: list[tuple[str, int, int]] = []

        service = AudioPostprocessingService(
            audio_preprocessor=BypassAudioPreprocessor(),
            speaker_diarizer=_FakeSpeakerDiarizer(
                [
                    SpeakerSegment("화자-A", 0, 320),
                    SpeakerSegment("화자-B", 600, 960),
                ]
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

        segments = service.build_speaker_transcript(
            wav_path,
            on_segment=lambda item: callback_segments.append(
                (item.speaker_label, item.start_ms, item.end_ms)
            ),
        )

        assert [(item.speaker_label, item.start_ms, item.end_ms) for item in segments] == callback_segments


def _write_pcm_wave(path: Path) -> None:
    raw_bytes = b"\x00\x00" * 16000
    with wave.open(str(path), "wb") as wav_file:
        wav_file.setnchannels(1)
        wav_file.setsampwidth(2)
        wav_file.setframerate(16000)
        wav_file.writeframes(raw_bytes)


