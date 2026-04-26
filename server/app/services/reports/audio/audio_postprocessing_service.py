"""오디오 영역의 audio postprocessing service 서비스를 제공한다."""
from __future__ import annotations

import hashlib
import json
import logging
from collections.abc import Callable
from dataclasses import asdict, dataclass, is_dataclass
from pathlib import Path
from time import perf_counter
from typing import Any

from server.app.services.audio.preprocessing.audio_preprocessing import AudioBuffer, AudioPreprocessor
from server.app.services.audio.segmentation.speech_segmenter import SpeechSegment
from server.app.services.audio.stt.transcription import SpeechToTextService
from server.app.services.audio.filters.transcription_guard import TranscriptionGuard
from server.app.services.audio.io.wav_chunk_reader import read_pcm_wave_file
from server.app.services.diarization.speaker_diarizer import SpeakerDiarizer, SpeakerSegment


_MIN_POSTPROCESSING_SEGMENT_MS = 120
_MERGEABLE_SAME_SPEAKER_GAP_MS = 180

logger = logging.getLogger(__name__)


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

    def build_speaker_transcript(
        self,
        audio_path: str | Path,
        *,
        on_segment: Callable[[SpeakerTranscriptSegment], None] | None = None,
    ) -> list[SpeakerTranscriptSegment]:
        """WAV 파일에서 화자별 전사 결과를 생성한다."""

        total_started_at = perf_counter()
        audio_path_text = str(audio_path)
        processed_audio = self.load_audio(audio_path)
        diarized_segments = self.diarize_audio(
            processed_audio,
            audio_path=audio_path_text,
        )
        transcripts = self.transcribe_segments(
            processed_audio,
            diarized_segments,
            audio_path=audio_path_text,
            on_segment=on_segment,
        )
        logger.info(
            "audio post-processing 전체 완료: audio_path=%s elapsed_seconds=%.3f transcript_segment_count=%s",
            audio_path_text,
            perf_counter() - total_started_at,
            len(transcripts),
        )
        return transcripts

    def build_stage_cache_signature(self) -> str:
        """후처리 stage cache 무효화에 사용할 backend/config signature를 만든다."""

        payload = {
            "service": _qualified_type_name(self),
            "audio_preprocessor": _component_signature(self._audio_preprocessor),
            "speaker_diarizer": _component_signature(self._speaker_diarizer),
            "speech_to_text_service": _component_signature(
                self._speech_to_text_service
            ),
            "transcription_guard": _component_signature(self._transcription_guard),
            "expected_sample_rate_hz": self._expected_sample_rate_hz,
            "expected_sample_width_bytes": self._expected_sample_width_bytes,
            "expected_channels": self._expected_channels,
        }
        encoded = json.dumps(
            _stable_json_value(payload),
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
        return hashlib.sha256(encoded).hexdigest()

    def load_audio(self, audio_path: str | Path) -> AudioBuffer:
        """WAV 파일을 읽고 전처리한 오디오 버퍼를 반환한다."""

        audio_path_text = str(audio_path)
        stage_started_at = perf_counter()
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
        logger.info(
            "audio post-processing stage 완료: audio_path=%s stage=read_wav elapsed_seconds=%.3f duration_ms=%s raw_bytes=%s sample_rate_hz=%s channels=%s",
            audio_path_text,
            perf_counter() - stage_started_at,
            audio.duration_ms,
            len(audio.raw_bytes),
            audio.sample_rate_hz,
            audio.channels,
        )

        stage_started_at = perf_counter()
        processed_audio = self._audio_preprocessor.preprocess(audio)
        logger.info(
            "audio post-processing stage 완료: audio_path=%s stage=preprocess elapsed_seconds=%.3f duration_ms=%s raw_bytes=%s backend=%s",
            audio_path_text,
            perf_counter() - stage_started_at,
            processed_audio.duration_ms,
            len(processed_audio.raw_bytes),
            type(self._audio_preprocessor).__name__,
        )
        return processed_audio

    def diarize_audio(
        self,
        processed_audio: AudioBuffer,
        *,
        audio_path: str | Path | None = None,
    ) -> list[SpeakerSegment]:
        """전처리된 오디오에서 화자 구간을 추정하고 정규화한다."""

        audio_path_text = str(audio_path) if audio_path is not None else "-"
        stage_started_at = perf_counter()
        raw_diarized_segments = self._speaker_diarizer.diarize(processed_audio)
        logger.info(
            "audio post-processing stage 완료: audio_path=%s stage=diarize elapsed_seconds=%.3f raw_segment_count=%s backend=%s",
            audio_path_text,
            perf_counter() - stage_started_at,
            len(raw_diarized_segments),
            type(self._speaker_diarizer).__name__,
        )

        stage_started_at = perf_counter()
        diarized_segments = _normalize_diarized_segments(raw_diarized_segments)
        logger.info(
            "audio post-processing stage 완료: audio_path=%s stage=normalize_segments elapsed_seconds=%.3f raw_segment_count=%s normalized_segment_count=%s",
            audio_path_text,
            perf_counter() - stage_started_at,
            len(raw_diarized_segments),
            len(diarized_segments),
        )
        return diarized_segments

    def transcribe_segments(
        self,
        processed_audio: AudioBuffer,
        diarized_segments: list[SpeakerSegment],
        *,
        audio_path: str | Path | None = None,
        on_segment: Callable[[SpeakerTranscriptSegment], None] | None = None,
    ) -> list[SpeakerTranscriptSegment]:
        """화자 구간별 STT를 수행해 화자별 전사 결과를 만든다."""

        audio_path_text = str(audio_path) if audio_path is not None else "-"
        stage_started_at = perf_counter()
        transcripts: list[SpeakerTranscriptSegment] = []
        stt_call_count = 0
        skipped_short_count = 0
        skipped_empty_count = 0
        dropped_by_guard_count = 0
        for speaker_segment in diarized_segments:
            # 너무 짧은 조각은 hallucination 비율이 높아서 노트 후처리에서는 버린다.
            if speaker_segment.end_ms - speaker_segment.start_ms < _MIN_POSTPROCESSING_SEGMENT_MS:
                skipped_short_count += 1
                continue
            segment_bytes = _slice_pcm_bytes(
                processed_audio,
                speaker_segment.start_ms,
                speaker_segment.end_ms,
            )
            if not segment_bytes:
                skipped_empty_count += 1
                continue
            stt_call_count += 1
            transcription = self._speech_to_text_service.transcribe(
                SpeechSegment(
                    raw_bytes=segment_bytes,
                    start_ms=speaker_segment.start_ms,
                    end_ms=speaker_segment.end_ms,
                )
            )
            if not self._transcription_guard.should_keep(transcription):
                dropped_by_guard_count += 1
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
        logger.info(
            "audio post-processing stage 완료: audio_path=%s stage=stt_per_segment elapsed_seconds=%.3f normalized_segment_count=%s stt_call_count=%s kept_segment_count=%s skipped_short_count=%s skipped_empty_count=%s dropped_by_guard_count=%s backend=%s",
            audio_path_text,
            perf_counter() - stage_started_at,
            len(diarized_segments),
            stt_call_count,
            len(transcripts),
            skipped_short_count,
            skipped_empty_count,
            dropped_by_guard_count,
            type(self._speech_to_text_service).__name__,
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


def _normalize_diarized_segments(
    diarized_segments: list[SpeakerSegment],
) -> list[SpeakerSegment]:
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


def _component_signature(component: object) -> dict[str, Any]:
    config = getattr(component, "_config", None)
    payload: dict[str, Any] = {"type": _qualified_type_name(component)}
    if config is not None:
        payload["config"] = _stable_json_value(
            asdict(config) if is_dataclass(config) else config
        )
    return payload


def _qualified_type_name(value: object) -> str:
    value_type = type(value)
    return f"{value_type.__module__}.{value_type.__qualname__}"


def _stable_json_value(value: Any) -> Any:
    if isinstance(value, Path):
        return str(value)
    if is_dataclass(value) and not isinstance(value, type):
        return _stable_json_value(asdict(value))
    if isinstance(value, dict):
        return {
            str(key): _stable_json_value(item)
            for key, item in sorted(value.items(), key=lambda pair: str(pair[0]))
        }
    if isinstance(value, (list, tuple)):
        return [_stable_json_value(item) for item in value]
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    return repr(value)
