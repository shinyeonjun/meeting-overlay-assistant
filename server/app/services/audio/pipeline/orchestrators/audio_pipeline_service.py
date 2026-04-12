"""오디오 입력부터 발화와 이벤트 생성까지 연결하는 파이프라인 오케스트레이터."""

from __future__ import annotations

from server.app.core.persistence_types import TransactionManager
from server.app.domain.models.meeting_event import MeetingEvent
from server.app.domain.models.utterance import Utterance
from server.app.repositories.contracts.utterance_repository import UtteranceRepository
from server.app.services.analysis.analyzers.analyzer import MeetingAnalyzer
from server.app.services.analysis.correction.live_event_correction_service import (
    AsyncLiveEventCorrectionService,
    NoOpLiveEventCorrectionService,
)
from server.app.services.audio.filters.audio_content_gate import AudioContentGate
from server.app.services.audio.filters.transcription_guard import TranscriptionGuard
from server.app.services.audio.pipeline.common.pipeline_text import (
    compact_length,
    normalize_text,
    now_ms,
)
from server.app.services.audio.pipeline.final import final_flow
from server.app.services.audio.pipeline.models.live_stream_utterance import LiveStreamUtterance
from server.app.services.audio.pipeline.orchestrators.helpers import (
    build_alignment_manager,
    configure_audio_pipeline_service,
    initialize_runtime_lanes,
    process_chunk,
    process_final_chunk,
    process_preview_chunk,
    reset_runtime_streams,
    split_runtime_lane_services,
    supports_preview,
)
from server.app.services.audio.pipeline.preview import preview_flow
from server.app.services.audio.segmentation.speech_segmenter import AudioSegmenter
from server.app.services.audio.stt.transcription import SpeechToTextService, StreamingSpeechToTextService
from server.app.services.events.meeting_event_service import MeetingEventService
from server.app.services.observability.runtime.runtime_monitor_service import RuntimeMonitorService


class AudioPipelineService:
    """오디오 chunk를 preview/final/archive 결과로 조립하는 오케스트레이터."""

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
        live_question_dispatcher=None,
        transaction_manager: TransactionManager | None = None,
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
        configure_audio_pipeline_service(
            self,
            segmenter=segmenter,
            speech_to_text_service=speech_to_text_service,
            analyzer_service=analyzer_service,
            utterance_repository=utterance_repository,
            event_service=event_service,
            transcription_guard=transcription_guard,
            content_gate=content_gate,
            live_event_corrector=live_event_corrector,
            live_question_dispatcher=live_question_dispatcher,
            transaction_manager=transaction_manager,
            duplicate_window_ms=duplicate_window_ms,
            duplicate_similarity_threshold=duplicate_similarity_threshold,
            duplicate_max_confidence=duplicate_max_confidence,
            preview_min_compact_length=preview_min_compact_length,
            preview_backpressure_queue_delay_ms=preview_backpressure_queue_delay_ms,
            preview_backpressure_hold_chunks=preview_backpressure_hold_chunks,
            segment_grace_match_max_gap_ms=segment_grace_match_max_gap_ms,
            live_final_emit_max_delay_ms=live_final_emit_max_delay_ms,
            live_final_initial_grace_segments=live_final_initial_grace_segments,
            live_final_initial_grace_delay_ms=live_final_initial_grace_delay_ms,
            final_short_text_max_compact_length=final_short_text_max_compact_length,
            final_short_text_min_confidence=final_short_text_min_confidence,
            runtime_monitor_service=runtime_monitor_service,
        )

    def supports_preview(self) -> bool:
        """현재 STT 서비스가 preview 경로를 지원하는지 반환한다."""

        return supports_preview(self)

    def reset_runtime_streams(self) -> None:
        """preview/final runtime lane 스트림 상태를 초기화한다."""

        reset_runtime_streams(self)

    def process_chunk(
        self,
        session_id: str,
        chunk: bytes,
        input_source: str | None = None,
    ) -> tuple[list[Utterance | LiveStreamUtterance], list[MeetingEvent]]:
        """오디오 chunk를 처리하고 생성된 발화/이벤트를 반환한다."""

        return process_chunk(self, session_id, chunk, input_source)

    def process_preview_chunk(
        self,
        session_id: str,
        chunk: bytes,
        input_source: str | None = None,
        preview_cycle_id: int | None = None,
    ) -> list[LiveStreamUtterance]:
        """실시간 preview/live_final 발화만 생성한다."""

        return process_preview_chunk(
            self,
            session_id,
            chunk,
            input_source,
            preview_cycle_id,
        )

    def process_final_chunk(
        self,
        session_id: str,
        chunk: bytes,
        input_source: str | None = None,
    ) -> tuple[list[LiveStreamUtterance], list[MeetingEvent]]:
        """최종 발화와 이벤트만 생성한다."""

        return process_final_chunk(self, session_id, chunk, input_source)

    def _process_segments(self, **kwargs) -> None:
        final_flow.process_segments(self, **kwargs)

    def _build_preview_utterances(self, session_id: str, chunk: bytes, *, input_source: str | None, preview_cycle_id: int | None) -> list[LiveStreamUtterance]:
        return preview_flow.build_preview_utterances(
            self,
            session_id,
            chunk,
            input_source=input_source,
            preview_cycle_id=preview_cycle_id,
        )

    def _consume_early_eou_hint(self) -> bool:
        return preview_flow.consume_early_eou_hint(self)

    def _consume_segment_binding_for_final(self, utterance: Utterance) -> tuple[str, int | None, str]:
        return final_flow.consume_segment_binding_for_final(self, utterance)

    def _apply_preview_backpressure(self, *, session_id: str, final_queue_delay_ms: int) -> None:
        final_flow.apply_preview_backpressure(
            self,
            session_id=session_id,
            final_queue_delay_ms=final_queue_delay_ms,
        )

    def _should_emit_live_final(self, final_queue_delay_ms: int) -> bool:
        return final_flow.should_emit_live_final(self, final_queue_delay_ms)

    def _resolve_live_final_delay_threshold_ms(self) -> int:
        return final_flow.resolve_live_final_delay_threshold_ms(self)

    def _record_alignment_status(self, session_id: str, alignment_status: str) -> None:
        final_flow.record_alignment_status(self, session_id, alignment_status)

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
        return final_flow.should_skip_duplicate_transcription(
            self,
            session_id=session_id,
            text=text,
            confidence=confidence,
            start_ms=start_ms,
            end_ms=end_ms,
            connection=connection,
        )

    def _should_keep_preview(self, result) -> tuple[bool, str | None]:
        return preview_flow.should_keep_preview(self, result)

    def _should_keep_short_final(self, result) -> tuple[bool, str | None]:
        return final_flow.should_keep_short_final(self, result)

    @staticmethod
    def _split_runtime_lane_services(
        speech_to_text_service: SpeechToTextService,
    ) -> tuple[StreamingSpeechToTextService | None, SpeechToTextService]:
        return split_runtime_lane_services(speech_to_text_service)

    @staticmethod
    def _build_alignment_manager(
        *,
        preview_backpressure_queue_delay_ms: int,
        preview_backpressure_hold_chunks: int,
        segment_grace_match_max_gap_ms: int,
    ):
        return build_alignment_manager(
            preview_backpressure_queue_delay_ms=preview_backpressure_queue_delay_ms,
            preview_backpressure_hold_chunks=preview_backpressure_hold_chunks,
            segment_grace_match_max_gap_ms=segment_grace_match_max_gap_ms,
        )

    @staticmethod
    def _normalize_text(text: str) -> str:
        return normalize_text(text)

    @staticmethod
    def _compact_length(text: str) -> int:
        return compact_length(text)

    @staticmethod
    def _now_ms() -> int:
        return now_ms()

    def _resolve_stt_backend_name(self) -> str:
        return final_flow.resolve_backend_name(self)

    def _record_chunk_processed(
        self,
        *,
        session_id: str,
        utterance_count: int,
        event_count: int,
    ) -> None:
        final_flow.record_chunk_processed(
            self,
            session_id=session_id,
            utterance_count=utterance_count,
            event_count=event_count,
        )

    def _record_processing_error(self, scope: str, message: str) -> None:
        final_flow.record_processing_error(self, scope, message)

    def _remember_live_final_candidate(
        self,
        *,
        segment_id: str,
        text: str,
        emitted_at_ms: int,
    ) -> None:
        preview_flow.remember_live_final_candidate(
            self,
            segment_id=segment_id,
            text=text,
            emitted_at_ms=emitted_at_ms,
        )

    def _consume_live_final_comparison(
        self,
        *,
        segment_id: str,
        archive_text: str,
        archive_emitted_at_ms: int,
    ) -> dict[str, object] | None:
        return preview_flow.consume_live_final_comparison(
            self,
            segment_id=segment_id,
            archive_text=archive_text,
            archive_emitted_at_ms=archive_emitted_at_ms,
        )
