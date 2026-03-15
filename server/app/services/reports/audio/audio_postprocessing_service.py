"""회의 후 오디오 파일 전처리/화자 분리/STT 파이프라인."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from server.app.services.audio.preprocessing.audio_preprocessing import AudioBuffer, AudioPreprocessor
from server.app.services.audio.segmentation.speech_segmenter import SpeechSegment
from server.app.services.audio.stt.transcription import SpeechToTextService
from server.app.services.audio.filters.transcription_guard import TranscriptionGuard
from server.app.services.audio.io.wav_chunk_reader import read_pcm_wave_file
from server.app.services.diarization.speaker_diarizer import SpeakerDiarizer


@dataclass(frozen=True)
class SpeakerTranscriptSegment:
    """화자별 전사 결과."""

    speaker_label: str
    start_ms: int
    end_ms: int
    text: str
    confidence: float


class AudioPostprocessingService:
    """오디오 파일을 전처리하고 화자별 전사 결과를 생성한다."""

    def __init__(
        self,
        audio_preprocessor: AudioPreprocessor,
        speaker_diarizer: SpeakerDiarizer,
        speech_to_text_service: SpeechToTextService,
        transcription_guard: TranscriptionGuard,
        *,
        expected_sample_rate_hz: int,
        expected_sample_width_bytes: int,
        expected_channels: int,
    ) -> None:
        self._audio_preprocessor = audio_preprocessor
        self._speaker_diarizer = speaker_diarizer
        self._speech_to_text_service = speech_to_text_service
        self._transcription_guard = transcription_guard
        self._expected_sample_rate_hz = expected_sample_rate_hz
        self._expected_sample_width_bytes = expected_sample_width_bytes
        self._expected_channels = expected_channels

    def build_speaker_transcript(self, audio_path: str | Path) -> list[SpeakerTranscriptSegment]:
        """WAV 파일에서 화자별 전사 결과를 생성한다."""

        wave_audio = read_pcm_wave_file(
            audio_path,
            expected_sample_rate_hz=self._expected_sample_rate_hz,
            expected_sample_width_bytes=self._expected_sample_width_bytes,
            expected_channels=self._expected_channels,
        )
        audio = AudioBuffer(
            sample_rate_hz=wave_audio.sample_rate_hz,
            sample_width_bytes=wave_audio.sample_width_bytes,
            channels=wave_audio.channels,
            raw_bytes=wave_audio.raw_bytes,
        )
        processed_audio = self._audio_preprocessor.preprocess(audio)
        diarized_segments = self._speaker_diarizer.diarize(processed_audio)

        transcripts: list[SpeakerTranscriptSegment] = []
        for speaker_segment in diarized_segments:
            segment_bytes = _slice_pcm_bytes(processed_audio, speaker_segment.start_ms, speaker_segment.end_ms)
            if not segment_bytes:
                continue
            transcription = self._speech_to_text_service.transcribe(
                SpeechSegment(
                    raw_bytes=segment_bytes,
                    start_ms=speaker_segment.start_ms,
                    end_ms=speaker_segment.end_ms,
                )
            )
            if not self._transcription_guard.should_keep(transcription):
                continue
            transcripts.append(
                SpeakerTranscriptSegment(
                    speaker_label=speaker_segment.speaker_label,
                    start_ms=speaker_segment.start_ms,
                    end_ms=speaker_segment.end_ms,
                    text=transcription.text,
                    confidence=transcription.confidence,
                )
            )
        return transcripts


def _slice_pcm_bytes(audio: AudioBuffer, start_ms: int, end_ms: int) -> bytes:
    bytes_per_ms = audio.bytes_per_second / 1000
    start_index = max(int(start_ms * bytes_per_ms), 0)
    end_index = max(int(end_ms * bytes_per_ms), start_index)

    sample_size = max(audio.sample_width_bytes * audio.channels, 1)
    aligned_start = start_index - (start_index % sample_size)
    aligned_end = end_index - (end_index % sample_size)
    return audio.raw_bytes[aligned_start:aligned_end]


