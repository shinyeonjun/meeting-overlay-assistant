"""오디오 입력부터 발화와 이벤트 생성까지 연결하는 파이프라인."""

from __future__ import annotations

import logging
import re
import time
from dataclasses import replace
from difflib import SequenceMatcher

from server.app.domain.models.meeting_event import MeetingEvent
from server.app.domain.models.utterance import Utterance
from server.app.domain.shared.enums import EventType
from server.app.infrastructure.persistence.sqlite.database import Database
from server.app.repositories.contracts.utterance_repository import UtteranceRepository
from server.app.services.analysis.analyzers.analyzer import MeetingAnalyzer
from server.app.services.analysis.correction.live_event_correction_service import (
    AsyncLiveEventCorrectionService,
    NoOpLiveEventCorrectionService,
)
from server.app.services.audio.filters.audio_content_gate import AudioContentGate
from server.app.services.audio.pipeline.live_stream_utterance import LiveStreamUtterance
from server.app.services.audio.pipeline.stream_alignment_manager import StreamAlignmentManager
from server.app.services.audio.segmentation.speech_segmenter import AudioSegmenter
from server.app.services.audio.stt.transcription import (
    SpeechToTextService,
    StreamingSpeechToTextService,
)
from server.app.services.audio.filters.transcription_guard import TranscriptionGuard
from server.app.services.events.meeting_event_service import MeetingEventService
from server.app.services.observability.runtime_monitor_service import RuntimeMonitorService


logger = logging.getLogger(__name__)

_LIVE_EVENT_TYPES = {EventType.QUESTION}


class AudioPipelineService:
    """오디오 chunk를 발화와 이벤트로 바꾸는 스트림 서비스."""

    def __init__(
        self,
        segmenter: AudioSegmenter,
        speech_to_text_service: SpeechToTextService,
        analyzer_service: MeetingAnalyzer,
        utterance_repository: UtteranceRepository,
        event_service: MeetingEventService,
        transcription_guard: TranscriptionGuard,
        content_gate: AudioContentGate | None = None,
        live_event_corrector: AsyncLiveEventCorrectionService | NoOpLiveEventCorrectionService | None = None,
        transaction_manager: Database | None = None,
        duplicate_window_ms: int = 0,
        duplicate_similarity_threshold: float = 1.0,
        duplicate_max_confidence: float = 0.0,
        preview_min_compact_length: int = 1,
        preview_backpressure_queue_delay_ms: int = 0,
        preview_backpressure_hold_chunks: int = 0,
        segment_grace_match_max_gap_ms: int = 0,
        live_final_emit_max_delay_ms: int = 0,
        live_final_initial_grace_segments: int = 0,
        live_final_initial_grace_delay_ms: int = 0,
        final_short_text_max_compact_length: int = 0,
        final_short_text_min_confidence: float = 0.0,
        runtime_monitor_service: RuntimeMonitorService | None = None,
    ) -> None:
        self._segmenter = segmenter
        self._speech_to_text_service = speech_to_text_service
        self._analyzer_service = analyzer_service
        self._utterance_repository = utterance_repository
        self._event_service = event_service
        self._transcription_guard = transcription_guard
        self._content_gate = content_gate
        self._live_event_corrector = live_event_corrector or NoOpLiveEventCorrectionService()
        self._transaction_manager = transaction_manager
        self._duplicate_window_ms = duplicate_window_ms
        self._duplicate_similarity_threshold = duplicate_similarity_threshold
        self._duplicate_max_confidence = duplicate_max_confidence
        self._preview_min_compact_length = preview_min_compact_length
        self._preview_backpressure_queue_delay_ms = preview_backpressure_queue_delay_ms
        self._preview_backpressure_hold_chunks = preview_backpressure_hold_chunks
        self._segment_grace_match_max_gap_ms = segment_grace_match_max_gap_ms
        self._live_final_emit_max_delay_ms = live_final_emit_max_delay_ms
        self._live_final_initial_grace_segments = live_final_initial_grace_segments
        self._live_final_initial_grace_delay_ms = live_final_initial_grace_delay_ms
        self._final_short_text_max_compact_length = final_short_text_max_compact_length
        self._final_short_text_min_confidence = final_short_text_min_confidence
        self._runtime_monitor_service = runtime_monitor_service
        self._processed_final_count = 0
        self._alignment_manager = StreamAlignmentManager(
            preview_backpressure_queue_delay_ms=preview_backpressure_queue_delay_ms,
            preview_backpressure_hold_chunks=preview_backpressure_hold_chunks,
            segment_grace_match_max_gap_ms=segment_grace_match_max_gap_ms,
        )

    def supports_preview(self) -> bool:
        """현재 STT 서비스가 preview 경로를 지원하는지 반환한다."""

        return isinstance(self._speech_to_text_service, StreamingSpeechToTextService)

    def process_chunk(
        self,
        session_id: str,
        chunk: bytes,
        input_source: str | None = None,
    ) -> tuple[list[Utterance | LiveStreamUtterance], list[MeetingEvent]]:
        """오디오 chunk를 처리하고 생성된 발화/이벤트를 반환한다."""

        preview_utterances = self.process_preview_chunk(
            session_id,
            chunk,
            input_source,
        )
        outgoing_final_utterances, saved_events = self.process_final_chunk(
            session_id,
            chunk,
            input_source,
        )
        if outgoing_final_utterances:
            preview_utterances = []
        utterances = [*preview_utterances, *outgoing_final_utterances]
        return utterances, saved_events

    def process_preview_chunk(
        self,
        session_id: str,
        chunk: bytes,
        input_source: str | None = None,
    ) -> list[LiveStreamUtterance]:
        """실시간 preview 발화만 생성한다."""

        logger.debug("preview 청크 처리 시작: session_id=%s chunk_bytes=%d", session_id, len(chunk))
        try:
            preview_utterances = self._build_preview_utterances(
                session_id,
                chunk,
                input_source=input_source,
            )
            if preview_utterances:
                logger.info(
                    "partial 전사 생성: session_id=%s partials=%d segment_id=%s latest_revision=%s latest_text=%s",
                    session_id,
                    len(preview_utterances),
                    preview_utterances[-1].segment_id,
                    preview_utterances[-1].revision,
                    preview_utterances[-1].text,
                )
            return preview_utterances
        except Exception as error:
            self._record_processing_error("audio_pipeline.process_preview_chunk", str(error))
            raise

    def process_final_chunk(
        self,
        session_id: str,
        chunk: bytes,
        input_source: str | None = None,
    ) -> tuple[list[LiveStreamUtterance], list[MeetingEvent]]:
        """최종 발화와 이벤트만 생성한다."""

        logger.debug("final 청크 처리 시작: session_id=%s chunk_bytes=%d", session_id, len(chunk))
        try:
            saved_utterances: list[Utterance] = []
            outgoing_final_utterances: list[LiveStreamUtterance] = []
            saved_events: list[MeetingEvent] = []

            if self._transaction_manager is not None:
                with self._transaction_manager.transaction() as connection:
                    self._process_segments(
                        session_id=session_id,
                        chunk=chunk,
                        input_source=input_source,
                        saved_utterances=saved_utterances,
                        outgoing_final_utterances=outgoing_final_utterances,
                        saved_events=saved_events,
                        connection=connection,
                    )
            else:
                self._process_segments(
                    session_id=session_id,
                    chunk=chunk,
                    input_source=input_source,
                    saved_utterances=saved_utterances,
                    outgoing_final_utterances=outgoing_final_utterances,
                    saved_events=saved_events,
                    connection=None,
                )

            for utterance in saved_utterances:
                self._live_event_corrector.submit(utterance)

            if saved_utterances:
                self._alignment_manager.clear_active_preview()

            if outgoing_final_utterances or saved_events:
                logger.info(
                    "final 청크 처리 완료: session_id=%s utterances=%d events=%d",
                    session_id,
                    len(outgoing_final_utterances),
                    len(saved_events),
                )
            else:
                logger.debug("final 청크 처리 완료(빈 결과): session_id=%s", session_id)

            self._record_chunk_processed(
                session_id=session_id,
                utterance_count=len(outgoing_final_utterances),
                event_count=len(saved_events),
            )
            return outgoing_final_utterances, saved_events
        except Exception as error:
            self._record_processing_error("audio_pipeline.process_final_chunk", str(error))
            raise

    def _process_segments(
        self,
        *,
        session_id: str,
        chunk: bytes,
        input_source: str | None,
        saved_utterances: list[Utterance],
        outgoing_final_utterances: list[LiveStreamUtterance],
        saved_events: list[MeetingEvent],
        connection,
    ) -> None:
        for segment in self._iter_processable_segments(session_id=session_id, chunk=chunk):
            transcription, final_queue_delay_ms = self._transcribe_segment(
                session_id=session_id,
                segment=segment,
            )

            if self._is_rejected_transcription(session_id=session_id, transcription=transcription):
                continue

            if self._should_skip_duplicate_transcription(
                session_id=session_id,
                text=transcription.text,
                confidence=transcription.confidence,
                start_ms=segment.start_ms,
                end_ms=segment.end_ms,
                connection=connection,
            ):
                logger.info(
                    "인접 중복 전사 스킵: session_id=%s confidence=%.4f text=%s",
                    session_id,
                    transcription.confidence,
                    transcription.text,
                )
                continue

            self._save_final_utterance_and_events(
                session_id=session_id,
                segment=segment,
                transcription=transcription,
                final_queue_delay_ms=final_queue_delay_ms,
                input_source=input_source,
                saved_utterances=saved_utterances,
                outgoing_final_utterances=outgoing_final_utterances,
                saved_events=saved_events,
                connection=connection,
            )

    def _iter_processable_segments(self, *, session_id: str, chunk: bytes):
        for segment in self._segmenter.split(chunk):
            logger.debug(
                "세그먼트 처리: session_id=%s start_ms=%s end_ms=%s bytes=%d",
                session_id,
                segment.start_ms,
                segment.end_ms,
                len(segment.raw_bytes),
            )
            if self._content_gate is not None and not self._content_gate.should_process(segment):
                logger.info(
                    "오디오 content gate 차단: session_id=%s start_ms=%s end_ms=%s",
                    session_id,
                    segment.start_ms,
                    segment.end_ms,
                )
                continue
            yield segment

    def _transcribe_segment(self, *, session_id: str, segment):
        transcription = self._speech_to_text_service.transcribe(segment)
        final_queue_delay_ms = max(self._now_ms() - segment.end_ms, 0)
        logger.info(
            "전사 결과: session_id=%s start_ms=%s end_ms=%s final_queue_delay_ms=%s confidence=%.4f no_speech_prob=%s text=%s",
            session_id,
            segment.start_ms,
            segment.end_ms,
            final_queue_delay_ms,
            transcription.confidence,
            (
                f"{transcription.no_speech_prob:.4f}"
                if transcription.no_speech_prob is not None
                else "none"
            ),
            transcription.text,
        )
        self._apply_preview_backpressure(final_queue_delay_ms)
        return transcription, final_queue_delay_ms

    def _is_rejected_transcription(self, *, session_id: str, transcription) -> bool:
        keep_transcription, rejection_reason = self._transcription_guard.evaluate(transcription)
        if not keep_transcription:
            self._log_transcription_rejection(session_id, rejection_reason, transcription)
            return True

        keep_short_final, short_final_reason = self._should_keep_short_final(transcription)
        if not keep_short_final:
            self._log_transcription_rejection(session_id, short_final_reason, transcription)
            return True
        return False

    def _log_transcription_rejection(self, session_id: str, reason: str | None, transcription) -> None:
        logger.info(
            "전사 필터링: session_id=%s reason=%s confidence=%.4f no_speech_prob=%s text=%s",
            session_id,
            reason,
            transcription.confidence,
            (
                f"{transcription.no_speech_prob:.4f}"
                if transcription.no_speech_prob is not None
                else "none"
            ),
            transcription.text,
        )
        if self._runtime_monitor_service is not None:
            self._runtime_monitor_service.record_rejection(reason=reason)

    def _save_final_utterance_and_events(
        self,
        *,
        session_id: str,
        segment,
        transcription,
        final_queue_delay_ms: int,
        input_source: str | None,
        saved_utterances: list[Utterance],
        outgoing_final_utterances: list[LiveStreamUtterance],
        saved_events: list[MeetingEvent],
        connection,
    ) -> None:
        utterance = Utterance.create(
            session_id=session_id,
            seq_num=self._utterance_repository.next_sequence(session_id, connection=connection),
            start_ms=segment.start_ms,
            end_ms=segment.end_ms,
            text=transcription.text,
            confidence=transcription.confidence,
            input_source=input_source,
            stt_backend=self._resolve_stt_backend_name(),
            latency_ms=final_queue_delay_ms,
        )
        saved_utterance = self._utterance_repository.save(utterance, connection=connection)
        saved_utterances.append(saved_utterance)
        segment_id, outgoing_seq_num, alignment_status = self._consume_segment_binding_for_final(saved_utterance)
        emitted_live_final = self._should_emit_live_final(final_queue_delay_ms)
        if emitted_live_final:
            outgoing_final_utterances.append(
                LiveStreamUtterance.from_utterance(
                    saved_utterance,
                    segment_id=segment_id,
                    seq_num=outgoing_seq_num,
                    input_source=input_source,
                )
            )
        else:
            outgoing_final_utterances.append(
                LiveStreamUtterance.from_utterance(
                    saved_utterance,
                    segment_id=segment_id,
                    seq_num=outgoing_seq_num,
                    input_source=input_source,
                    kind="late_final",
                    stability="final",
                )
            )

        logger.debug(
            "발화 저장 완료: session_id=%s utterance_id=%s seq_num=%d segment_id=%s alignment=%s confidence=%.4f",
            session_id,
            saved_utterance.id,
            saved_utterance.seq_num,
            segment_id,
            alignment_status,
            saved_utterance.confidence,
        )
        logger.info(
            "segment 정합성: session_id=%s segment_id=%s alignment=%s final_queue_delay_ms=%s",
            session_id,
            segment_id,
            alignment_status,
            final_queue_delay_ms,
        )
        if not emitted_live_final:
            logger.info(
                "late final로 다운그레이드 전송: session_id=%s segment_id=%s final_queue_delay_ms=%s max_live_delay_ms=%s",
                session_id,
                segment_id,
                final_queue_delay_ms,
                self._resolve_live_final_delay_threshold_ms(),
            )
        self._record_alignment_status(session_id, alignment_status)
        if self._runtime_monitor_service is not None:
            self._runtime_monitor_service.record_final_transcription(
                session_id=session_id,
                final_queue_delay_ms=final_queue_delay_ms,
                emitted_live_final=emitted_live_final,
                alignment_status=alignment_status,
            )
        self._processed_final_count += 1

        for event in self._analyzer_service.analyze(saved_utterance):
            event_candidate = event
            if event_candidate.event_type not in _LIVE_EVENT_TYPES:
                continue
            if not event_candidate.evidence_text:
                event_candidate = replace(
                    event_candidate,
                    evidence_text=saved_utterance.text,
                )
            if event_candidate.input_source != input_source:
                event_candidate = replace(event_candidate, input_source=input_source)
            if event_candidate.insight_scope != "live":
                event_candidate = replace(event_candidate, insight_scope="live")
            saved_event = self._event_service.save_or_merge(
                event_candidate,
                connection=connection,
            )
            existing_index = next(
                (
                    index
                    for index, existing_event in enumerate(saved_events)
                    if existing_event.id == saved_event.id
                ),
                None,
            )
            if existing_index is None:
                saved_events.append(saved_event)
            else:
                saved_events[existing_index] = saved_event
            logger.debug(
                "이벤트 저장 완료: session_id=%s event_id=%s type=%s state=%s",
                session_id,
                saved_event.id,
                saved_event.event_type.value,
                saved_event.state.value,
            )

    def _build_preview_utterances(
        self,
        session_id: str,
        chunk: bytes,
        *,
        input_source: str | None,
    ) -> list[LiveStreamUtterance]:
        if not isinstance(self._speech_to_text_service, StreamingSpeechToTextService):
            return []

        should_suppress_preview, remaining_chunks = self._alignment_manager.tick_preview_backpressure()
        if should_suppress_preview:
            logger.info(
                "partial 전사 억제: reason=backpressure remaining_chunks=%d",
                remaining_chunks,
            )
            return []
        preview_results = self._speech_to_text_service.preview_chunk(chunk)
        if not preview_results:
            return []
        if self._consume_early_eou_hint():
            promoted_result = preview_results[-1]
            if getattr(promoted_result, "kind", "partial") == "partial":
                preview_results[-1] = replace(
                    promoted_result,
                    kind="fast_final",
                    stability="medium",
                )

        now_ms = self._now_ms()
        preview_utterances: list[LiveStreamUtterance] = []
        preview_seq_num: int | None = None
        preview_segment_id: str | None = None
        for result in preview_results:
            normalized_text = self._normalize_text(result.text)
            if not normalized_text:
                continue
            keep_preview, rejection_reason = self._transcription_guard.evaluate(result)
            if not keep_preview:
                logger.info(
                    "partial 전사 필터링: session_id=%s reason=%s confidence=%.4f no_speech_prob=%s text=%s",
                    session_id,
                    rejection_reason,
                    result.confidence,
                    (
                        f"{result.no_speech_prob:.4f}"
                        if result.no_speech_prob is not None
                        else "none"
                    ),
                    result.text,
                )
                continue
            keep_preview_length, preview_rejection_reason = self._should_keep_preview(result)
            if not keep_preview_length:
                logger.info(
                    "partial 전사 필터링: session_id=%s reason=%s confidence=%.4f no_speech_prob=%s text=%s",
                    session_id,
                    preview_rejection_reason,
                    result.confidence,
                    (
                        f"{result.no_speech_prob:.4f}"
                        if result.no_speech_prob is not None
                        else "none"
                    ),
                    result.text,
                )
                continue
            if preview_seq_num is None or preview_segment_id is None:
                preview_seq_num, preview_segment_id = self._alignment_manager.get_or_create_preview_binding()
            preview_utterances.append(
                LiveStreamUtterance.create(
                    seq_num=preview_seq_num,
                    segment_id=preview_segment_id,
                    start_ms=now_ms,
                    end_ms=now_ms,
                    text=result.text,
                    confidence=result.confidence,
                    kind=result.kind,
                    revision=result.revision,
                    input_source=input_source,
                    stability=getattr(result, "stability", None),
                )
            )

        if preview_utterances:
            if preview_seq_num is not None and preview_segment_id is not None:
                self._alignment_manager.mark_preview_emitted(
                    seq_num=preview_seq_num,
                    segment_id=preview_segment_id,
                    now_ms=now_ms,
                )

        return preview_utterances

    def _consume_early_eou_hint(self) -> bool:
        consume_hint = getattr(self._segmenter, "consume_early_eou_hint", None)
        if not callable(consume_hint):
            return False
        return bool(consume_hint())

    def _consume_segment_binding_for_final(self, utterance: Utterance) -> tuple[str, int | None, str]:
        return self._alignment_manager.consume_for_final(
            now_ms=self._now_ms(),
            start_ms=utterance.start_ms,
            end_ms=utterance.end_ms,
        )

    def _apply_preview_backpressure(self, final_queue_delay_ms: int) -> None:
        if not self._should_emit_live_final(final_queue_delay_ms):
            self._alignment_manager.clear_preview_backpressure()
            return
        activated, hold_chunks = self._alignment_manager.apply_final_queue_delay(final_queue_delay_ms)
        if not activated:
            return
        logger.info(
            "preview backpressure 활성화: final_queue_delay_ms=%d hold_chunks=%d",
            final_queue_delay_ms,
            hold_chunks,
        )
        if self._runtime_monitor_service is not None:
            self._runtime_monitor_service.record_preview_backpressure(
                final_queue_delay_ms=final_queue_delay_ms,
                hold_chunks=hold_chunks,
            )

    def _should_emit_live_final(self, final_queue_delay_ms: int) -> bool:
        if self._live_final_emit_max_delay_ms <= 0:
            return True
        return final_queue_delay_ms <= self._resolve_live_final_delay_threshold_ms()

    def _resolve_live_final_delay_threshold_ms(self) -> int:
        allowed_delay_ms = self._live_final_emit_max_delay_ms
        if (
            self._processed_final_count < self._live_final_initial_grace_segments
            and self._live_final_initial_grace_delay_ms > allowed_delay_ms
        ):
            return self._live_final_initial_grace_delay_ms
        return allowed_delay_ms

    def _record_alignment_status(self, session_id: str, alignment_status: str) -> None:
        counters = self._alignment_manager.record_alignment(alignment_status)
        logger.info(
            "segment 정합성 누적: session_id=%s matched=%d grace_matched=%d standalone=%d standalone_ratio=%.2f",
            session_id,
            counters.matched,
            counters.grace_matched,
            counters.standalone,
            counters.standalone_ratio,
        )

    def _should_skip_duplicate_transcription(
        self,
        *,
        session_id: str,
        text: str,
        confidence: float,
        start_ms: int,
        end_ms: int,
        connection,
    ) -> bool:
        if self._duplicate_window_ms <= 0:
            return False
        if confidence > self._duplicate_max_confidence:
            return False

        normalized_text = self._normalize_text(text)
        if not normalized_text:
            return False

        recent_utterances = self._utterance_repository.list_recent_by_session(
            session_id,
            limit=2,
            connection=connection,
        )
        for recent_utterance in recent_utterances:
            if recent_utterance.confidence > self._duplicate_max_confidence:
                continue
            if abs(start_ms - recent_utterance.end_ms) > self._duplicate_window_ms:
                continue
            recent_text = self._normalize_text(recent_utterance.text)
            if not recent_text:
                continue
            similarity = SequenceMatcher(a=normalized_text, b=recent_text).ratio()
            if similarity >= self._duplicate_similarity_threshold:
                return True

        return False

    @staticmethod
    def _normalize_text(text: str) -> str:
        return re.sub(r"\s+", " ", text.casefold()).strip()

    def _should_keep_preview(self, result) -> tuple[bool, str | None]:
        compact_length = self._compact_length(result.text)
        if compact_length < self._preview_min_compact_length:
            return False, "preview_too_short"
        return True, None

    def _should_keep_short_final(self, result) -> tuple[bool, str | None]:
        if self._final_short_text_max_compact_length <= 0:
            return True, None
        compact_length = self._compact_length(result.text)
        if compact_length > self._final_short_text_max_compact_length:
            return True, None
        if result.confidence >= self._final_short_text_min_confidence:
            return True, None
        return False, "short_final_low_confidence"

    @staticmethod
    def _compact_length(text: str) -> int:
        return len(re.sub(r"[\W_]+", "", text, flags=re.UNICODE))

    @staticmethod
    def _now_ms() -> int:
        return int(time.time() * 1000)

    def _resolve_stt_backend_name(self) -> str:
        backend_name = getattr(self._speech_to_text_service, "backend_name", None)
        if isinstance(backend_name, str) and backend_name.strip():
            return backend_name.strip()
        return self._speech_to_text_service.__class__.__name__

    def _record_chunk_processed(
        self,
        *,
        session_id: str,
        utterance_count: int,
        event_count: int,
    ) -> None:
        if self._runtime_monitor_service is None:
            return
        self._runtime_monitor_service.record_chunk_processed(
            session_id=session_id,
            utterance_count=utterance_count,
            event_count=event_count,
        )

    def _record_processing_error(self, scope: str, message: str) -> None:
        if self._runtime_monitor_service is None:
            return
        self._runtime_monitor_service.record_error(scope=scope, message=message)
