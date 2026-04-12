"""녹음 파일 기반 노트 후처리 STT를 담당한다.

live pipeline과 달리 이 서비스는 이미 저장된 파일을 다시 읽어 speaker
diarization과 segment 단위 STT를 수행한다. 목표는 "가장 빠른 결과"가 아니라
"노트용으로 다시 읽을 만한 안정적인 화자별 transcript"를 만드는 것이다.
"""
from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from server.app.services.audio.preprocessing.audio_preprocessing import AudioBuffer, AudioPreprocessor
from server.app.services.audio.segmentation.speech_segmenter import SpeechSegment
from server.app.services.audio.stt.transcription import SpeechToTextService
from server.app.services.audio.filters.transcription_guard import TranscriptionGuard
from server.app.services.audio.io.wav_chunk_reader import read_pcm_wave_file
from server.app.services.diarization.speaker_diarizer import SpeakerDiarizer, SpeakerSegment


_MIN_POSTPROCESSING_SEGMENT_MS = 120
_MERGEABLE_SAME_SPEAKER_GAP_MS = 180


@dataclass(frozen=True)
class SpeakerTranscriptSegment:
    """화자별 전사 결과.

    diarization 구간과 STT 결과를 같이 보존해서, 이후 canonical utterance
    생성이나 UI 초안 표시가 같은 구조를 공유할 수 있게 한다.
    """

    speaker_label: str
    start_ms: int
    end_ms: int
    text: str
    confidence: float


class AudioPostprocessingService:
    """오디오 파일을 전처리하고 화자별 전사 결과를 생성한다.

    이 서비스는 노트 재생성 시 "파일 -> 전처리 -> diarization -> segment STT"
    경로를 묶는다. 너무 짧은 조각은 버리고, 같은 화자의 인접 조각은 먼저
    병합해서 hallucination과 불필요한 STT 호출 수를 줄인다.
    """

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

    def build_speaker_transcript(
        self,
        audio_path: str | Path,
        *,
        on_segment: Callable[[SpeakerTranscriptSegment], None] | None = None,
    ) -> list[SpeakerTranscriptSegment]:
        """WAV 파일에서 화자별 전사 결과를 생성한다.

        `on_segment`가 주어지면 segment 하나가 끝날 때마다 callback을 호출한다.
        노트 재생성 UI에서 초안이 점진적으로 쌓이게 보이도록 하기 위한 경로다.
        """

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
        diarized_segments = _normalize_diarized_segments(
            self._speaker_diarizer.diarize(processed_audio)
        )

        transcripts: list[SpeakerTranscriptSegment] = []
        for speaker_segment in diarized_segments:
            # 너무 짧은 조각은 hallucination 비율이 높아서 노트 후처리에서는
            # 아예 STT를 태우지 않는다. 이 필터가 없으면 CTA, 아웃트로 같은
            # 잘못된 문구가 짧은 겹발화에서 튀는 빈도가 높아진다.
            if speaker_segment.end_ms - speaker_segment.start_ms < _MIN_POSTPROCESSING_SEGMENT_MS:
                continue
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
            transcript_segment = SpeakerTranscriptSegment(
                speaker_label=speaker_segment.speaker_label,
                start_ms=speaker_segment.start_ms,
                end_ms=speaker_segment.end_ms,
                text=transcription.text,
                confidence=transcription.confidence,
            )
            transcripts.append(transcript_segment)
            if on_segment is not None:
                # UI에서 초안 노트를 점진적으로 보여주기 위한 callback이다.
                on_segment(transcript_segment)
        return transcripts


def _slice_pcm_bytes(audio: AudioBuffer, start_ms: int, end_ms: int) -> bytes:
    """밀리초 범위를 PCM byte 범위로 안전하게 잘라낸다.

    sample boundary를 맞추지 않으면 채널, sample width가 틀어진 깨진 PCM
    조각이 생길 수 있어서 start/end index를 sample size 단위로 다시 맞춘다.
    """

    bytes_per_ms = audio.bytes_per_second / 1000
    start_index = max(int(start_ms * bytes_per_ms), 0)
    end_index = max(int(end_ms * bytes_per_ms), start_index)

    sample_size = max(audio.sample_width_bytes * audio.channels, 1)
    aligned_start = start_index - (start_index % sample_size)
    aligned_end = end_index - (end_index % sample_size)
    return audio.raw_bytes[aligned_start:aligned_end]


def _normalize_diarized_segments(
    diarized_segments: list[SpeakerSegment],
) -> list[SpeakerSegment]:
    """같은 화자의 인접 diarization 조각을 후처리용으로 병합한다.

    diarization은 같은 화자라도 짧은 gap을 두고 잘게 끊기는 경우가 많다.
    노트 후처리에서는 이런 조각을 그대로 STT에 태우는 것보다 먼저 합치는
    편이 더 안정적이다.
    """

    if not diarized_segments:
        return []

    normalized: list[SpeakerSegment] = []
    for segment in diarized_segments:
        if not normalized:
            normalized.append(segment)
            continue

        previous = normalized[-1]
        gap_ms = max(0, segment.start_ms - previous.end_ms)
        if (
            previous.speaker_label == segment.speaker_label
            and gap_ms <= _MERGEABLE_SAME_SPEAKER_GAP_MS
        ):
            normalized[-1] = SpeakerSegment(
                speaker_label=previous.speaker_label,
                start_ms=previous.start_ms,
                end_ms=max(previous.end_ms, segment.end_ms),
            )
            continue
        normalized.append(segment)

    return normalized
