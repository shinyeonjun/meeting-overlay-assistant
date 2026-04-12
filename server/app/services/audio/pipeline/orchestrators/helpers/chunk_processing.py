"""오디오 chunk 처리 helper."""

from __future__ import annotations

import logging

from server.app.domain.models.meeting_event import MeetingEvent
from server.app.domain.models.utterance import Utterance
from server.app.services.audio.pipeline.models.live_stream_utterance import (
    LiveStreamUtterance,
)


logger = logging.getLogger(__name__)


def process_chunk(
    service,
    session_id: str,
    chunk: bytes,
    input_source: str | None = None,
) -> tuple[list[Utterance | LiveStreamUtterance], list[MeetingEvent]]:
    """오디오 chunk를 preview/final/archive 결과로 조립한다."""

    preview_utterances = process_preview_chunk(
        service,
        session_id,
        chunk,
        input_source,
    )
    outgoing_final_utterances, saved_events = process_final_chunk(
        service,
        session_id,
        chunk,
        input_source,
    )
    if outgoing_final_utterances:
        preview_utterances = []
    utterances = [*preview_utterances, *outgoing_final_utterances]
    return utterances, saved_events


def process_preview_chunk(
    service,
    session_id: str,
    chunk: bytes,
    input_source: str | None = None,
    preview_cycle_id: int | None = None,
) -> list[LiveStreamUtterance]:
    """실시간 preview/live_final 발화만 생성한다."""

    logger.debug("preview 청크 처리 시작: session_id=%s chunk_bytes=%d", session_id, len(chunk))
    try:
        if service._runtime_monitor_service is not None:
            service._runtime_monitor_service.record_preview_stage(
                session_id=session_id,
                stage="job_started",
                preview_cycle_id=preview_cycle_id,
            )
        preview_utterances = service._build_preview_utterances(
            session_id,
            chunk,
            input_source=input_source,
            preview_cycle_id=preview_cycle_id,
        )
        if preview_utterances:
            logger.info(
                "preview 전사 생성: session_id=%s previews=%d segment_id=%s latest_revision=%s latest_text=%s",
                session_id,
                len(preview_utterances),
                preview_utterances[-1].segment_id,
                preview_utterances[-1].revision,
                preview_utterances[-1].text,
            )
        return preview_utterances
    except Exception as error:
        service._record_processing_error("audio_pipeline.process_preview_chunk", str(error))
        raise


def process_final_chunk(
    service,
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

        process_kwargs = {
            "session_id": session_id,
            "chunk": chunk,
            "input_source": input_source,
            "saved_utterances": saved_utterances,
            "outgoing_final_utterances": outgoing_final_utterances,
            "saved_events": saved_events,
        }
        if service._transaction_manager is not None:
            with service._transaction_manager.transaction() as connection:
                service._process_segments(
                    **process_kwargs,
                    connection=connection,
                )
        else:
            service._process_segments(
                **process_kwargs,
                connection=None,
            )

        for utterance in saved_utterances:
            if service._live_question_analysis_enabled:
                service._live_question_dispatcher.submit(utterance)
            elif service._persist_live_runtime_data:
                service._live_event_corrector.submit(utterance)

        if saved_utterances:
            service._coordination_state.clear_active_preview()

        if outgoing_final_utterances or saved_events:
            logger.info(
                "final 청크 처리 완료: session_id=%s utterances=%d events=%d",
                session_id,
                len(outgoing_final_utterances),
                len(saved_events),
            )
        else:
            logger.debug("final 청크 처리 완료(빈 결과): session_id=%s", session_id)

        service._record_chunk_processed(
            session_id=session_id,
            utterance_count=len(outgoing_final_utterances),
            event_count=len(saved_events),
        )
        return outgoing_final_utterances, saved_events
    except Exception as error:
        service._record_processing_error("audio_pipeline.process_final_chunk", str(error))
        raise
