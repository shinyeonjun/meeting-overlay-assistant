"""?ㅼ떆媛??ㅻ뵒???뚯씠?꾨씪??lane蹂??곹깭 而⑦뀒?대꼫."""

from __future__ import annotations

from collections import OrderedDict
from dataclasses import dataclass, field
from threading import RLock

from server.app.services.audio.pipeline.alignment.stream_alignment_manager import StreamAlignmentManager
from server.app.services.audio.pipeline.models.live_stream_utterance import (
    LiveStreamUtterance,
)
from server.app.services.audio.segmentation.speech_segmenter import AudioSegmenter
from server.app.services.audio.stt.transcription import (
    SpeechToTextService,
    StreamingSpeechToTextService,
)


@dataclass(slots=True)
class AudioPipelinePreviewLaneState:
    """preview lane ?꾩슜 ?곹깭瑜??대뒗??"""

    speech_to_text_service: StreamingSpeechToTextService | None


@dataclass(slots=True)
class AudioPipelineFinalLaneState:
    """final lane ?꾩슜 ?곹깭瑜??대뒗??"""

    segmenter: AudioSegmenter
    speech_to_text_service: SpeechToTextService
    processed_final_count: int = 0


@dataclass(slots=True)
class AudioPipelineCoordinationState:
    """preview/final??怨듭쑀?섎뒗 ?뺥빀???곹깭瑜?愿由ы븳??"""

    alignment_manager: StreamAlignmentManager
    recent_live_final_candidate_limit: int = 80
    recent_live_final_candidates: OrderedDict[str, dict[str, object]] = field(
        default_factory=OrderedDict
    )
    pending_final_caption_limit: int = 32
    pending_final_captions: OrderedDict[str, dict[str, object]] = field(
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

    def take_pending_final_caption(
        self,
        *,
        session_id: str,
        input_source: str | None,
    ) -> dict[str, object] | None:
        with self._lock:
            key = self._pending_final_caption_key(
                session_id=session_id,
                input_source=input_source,
            )
            return self.pending_final_captions.pop(key, None)

    def remember_pending_final_caption(
        self,
        *,
        session_id: str,
        input_source: str | None,
        payload: LiveStreamUtterance,
        hold_until_ms: int,
    ) -> None:
        with self._lock:
            key = self._pending_final_caption_key(
                session_id=session_id,
                input_source=input_source,
            )
            self.pending_final_captions[key] = {
                "session_id": session_id,
                "input_source": input_source,
                "payload": payload,
                "hold_until_ms": hold_until_ms,
            }
            self.pending_final_captions.move_to_end(key)
            while len(self.pending_final_captions) > self.pending_final_caption_limit:
                self.pending_final_captions.popitem(last=False)

    def pop_ready_pending_final_captions(
        self,
        *,
        now_ms: int,
        session_id: str | None = None,
        input_source: str | None = None,
        force: bool = False,
    ) -> list[LiveStreamUtterance]:
        ready: list[LiveStreamUtterance] = []
        with self._lock:
            for key, entry in list(self.pending_final_captions.items()):
                if session_id is not None and entry.get("session_id") != session_id:
                    continue
                if input_source is not None and entry.get("input_source") != input_source:
                    continue
                hold_until_ms = int(entry.get("hold_until_ms") or 0)
                if not force and hold_until_ms > now_ms:
                    continue
                payload = entry.get("payload")
                if isinstance(payload, LiveStreamUtterance):
                    ready.append(payload)
                self.pending_final_captions.pop(key, None)
        return ready

    @staticmethod
    def _pending_final_caption_key(
        *,
        session_id: str,
        input_source: str | None,
    ) -> str:
        normalized_input_source = input_source or "__default__"
        return f"{session_id}:{normalized_input_source}"
