"""오디오 영역의 runtime lane state 서비스를 제공한다."""
from __future__ import annotations

from collections import OrderedDict
from dataclasses import dataclass, field
from threading import RLock

from server.app.services.audio.pipeline.alignment.stream_alignment_manager import StreamAlignmentManager
from server.app.services.audio.segmentation.speech_segmenter import AudioSegmenter
from server.app.services.audio.stt.transcription import (
    SpeechToTextService,
    StreamingSpeechToTextService,
)


@dataclass(slots=True)
class AudioPipelinePreviewLaneState:
    """오디오 영역의 AudioPipelinePreviewLaneState 행위를 담당한다."""

    speech_to_text_service: StreamingSpeechToTextService | None


@dataclass(slots=True)
class AudioPipelineFinalLaneState:
    """오디오 영역의 AudioPipelineFinalLaneState 행위를 담당한다."""

    segmenter: AudioSegmenter
    speech_to_text_service: SpeechToTextService
    processed_final_count: int = 0


@dataclass(slots=True)
class AudioPipelineCoordinationState:
    """오디오 영역의 AudioPipelineCoordinationState 행위를 담당한다."""

    alignment_manager: StreamAlignmentManager
    recent_live_final_candidate_limit: int = 80
    recent_live_final_candidates: OrderedDict[str, dict[str, object]] = field(
        default_factory=OrderedDict
    )
    _lock: RLock = field(default_factory=RLock)

    def clear_active_preview(self) -> None:
        with self._lock:
            self.alignment_manager.clear_active_preview()

    def tick_preview_backpressure(self) -> tuple[bool, int]:
        with self._lock:
            return self.alignment_manager.tick_preview_backpressure()

    def get_or_create_preview_binding(self) -> tuple[int, str]:
        with self._lock:
            return self.alignment_manager.get_or_create_preview_binding()

    def mark_preview_emitted(
        self,
        *,
        seq_num: int,
        segment_id: str,
        now_ms: int,
    ) -> None:
        with self._lock:
            self.alignment_manager.mark_preview_emitted(
                seq_num=seq_num,
                segment_id=segment_id,
                now_ms=now_ms,
            )

    def consume_for_final(
        self,
        *,
        now_ms: int,
        start_ms: int,
        end_ms: int,
    ) -> tuple[str, int | None, str]:
        with self._lock:
            return self.alignment_manager.consume_for_final(
                now_ms=now_ms,
                start_ms=start_ms,
                end_ms=end_ms,
            )

    def clear_preview_backpressure(self) -> None:
        with self._lock:
            self.alignment_manager.clear_preview_backpressure()

    def apply_final_queue_delay(self, final_queue_delay_ms: int) -> tuple[bool, int]:
        with self._lock:
            return self.alignment_manager.apply_final_queue_delay(final_queue_delay_ms)

    def record_alignment(self, alignment_status: str):
        with self._lock:
            return self.alignment_manager.record_alignment(alignment_status)

    def remember_live_final_candidate(
        self,
        *,
        segment_id: str,
        text: str,
        emitted_at_ms: int,
    ) -> None:
        with self._lock:
            self.recent_live_final_candidates[segment_id] = {
                "text": text,
                "emitted_at_ms": emitted_at_ms,
            }
            self.recent_live_final_candidates.move_to_end(segment_id)
            while (
                len(self.recent_live_final_candidates)
                > self.recent_live_final_candidate_limit
            ):
                self.recent_live_final_candidates.popitem(last=False)

    def consume_live_final_candidate(
        self,
        *,
        segment_id: str,
    ) -> dict[str, object] | None:
        with self._lock:
            return self.recent_live_final_candidates.pop(segment_id, None)
