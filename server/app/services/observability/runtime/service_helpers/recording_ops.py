"""Runtime monitor 기록 helper."""

from __future__ import annotations

from server.app.services.observability.runtime.recorders.finals import (
    record_final_transcription as append_final_transcription,
)
from server.app.services.observability.runtime.recorders.previews import (
    record_preview_backpressure as append_preview_backpressure,
    record_preview_candidate as append_preview_candidate,
    record_preview_emitted as append_preview_emitted,
    record_preview_rejection as append_preview_rejection,
    record_preview_skip as append_preview_skip,
    record_preview_stage as append_preview_stage,
)
from server.app.services.observability.runtime.recorders.runtime_events import (
    record_chunk_processed as append_chunk_processed,
    record_error as append_error,
    record_rejection as append_rejection,
)


def record_final_transcription(
    service,
    *,
    session_id: str,
    final_queue_delay_ms: int,
    emitted_live_final: bool,
    alignment_status: str,
    live_final_compare_count: int = 0,
    live_final_changed: bool = False,
    live_final_similarity: float | None = None,
    live_final_delay_ms: int | None = None,
) -> None:
    """최종 전사 결과와 지표 상태를 기록한다."""

    with service._lock:
        append_final_transcription(
            service._state,
            session_id=session_id,
            final_queue_delay_ms=final_queue_delay_ms,
            emitted_live_final=emitted_live_final,
            alignment_status=alignment_status,
            live_final_compare_count=live_final_compare_count,
            live_final_changed=live_final_changed,
            live_final_similarity=live_final_similarity,
            live_final_delay_ms=live_final_delay_ms,
        )


def record_preview_candidate(
    service,
    *,
    session_id: str,
    kind: str,
    preview_cycle_id: int | None = None,
) -> None:
    """preview/live_final 후보 생성 사실을 기록한다."""

    with service._lock:
        append_preview_candidate(
            service._state,
            session_id=session_id,
            kind=kind,
            preview_cycle_id=preview_cycle_id,
        )


def record_preview_emitted(
    service,
    *,
    session_id: str,
    kind: str,
    preview_cycle_id: int | None = None,
) -> None:
    """preview/live_final 실제 전송 사실을 기록한다."""

    with service._lock:
        append_preview_emitted(
            service._state,
            session_id=session_id,
            kind=kind,
            preview_cycle_id=preview_cycle_id,
        )


def record_preview_stage(
    service,
    *,
    session_id: str,
    stage: str,
    pending_final_chunk_count: int | None = None,
    busy_worker_count: int | None = None,
    preview_cycle_id: int | None = None,
) -> None:
    """preview 처리 단계 timestamp를 기록한다."""

    with service._lock:
        append_preview_stage(
            service._state,
            session_id=session_id,
            stage=stage,
            pending_final_chunk_count=pending_final_chunk_count,
            busy_worker_count=busy_worker_count,
            preview_cycle_id=preview_cycle_id,
        )


def record_preview_skip(
    service,
    *,
    session_id: str,
    reason: str,
    pending_final_chunk_count: int | None,
    has_pending_preview_chunk: bool | None,
    busy_worker_count: int | None,
    busy_job_kind: str | None,
) -> None:
    """preview ready/pick 이전 skip 사유를 기록한다."""

    with service._lock:
        append_preview_skip(
            service._state,
            session_id=session_id,
            reason=reason,
            pending_final_chunk_count=pending_final_chunk_count,
            has_pending_preview_chunk=has_pending_preview_chunk,
            busy_worker_count=busy_worker_count,
            busy_job_kind=busy_job_kind,
        )


def record_preview_rejection(
    service,
    *,
    session_id: str,
    reason: str | None,
    filter_stage: str,
) -> None:
    """preview 후보가 필터에서 잘린 사실을 기록한다."""

    with service._lock:
        append_preview_rejection(
            service._state,
            session_id=session_id,
            reason=reason,
            filter_stage=filter_stage,
        )


def record_preview_backpressure(
    service,
    *,
    session_id: str | None = None,
    final_queue_delay_ms: int,
    hold_chunks: int,
) -> None:
    """preview backpressure 발생을 기록한다."""

    with service._lock:
        append_preview_backpressure(
            service._state,
            session_id=session_id,
            final_queue_delay_ms=final_queue_delay_ms,
            hold_chunks=hold_chunks,
        )


def record_rejection(service, *, reason: str | None) -> None:
    """전사 필터 사유를 기록한다."""

    with service._lock:
        append_rejection(service._state, reason=reason)


def record_chunk_processed(
    service,
    *,
    session_id: str,
    utterance_count: int,
    event_count: int,
) -> None:
    """chunk 처리 결과를 기록한다."""

    with service._lock:
        append_chunk_processed(
            service._state,
            session_id=session_id,
            utterance_count=utterance_count,
            event_count=event_count,
        )


def record_error(service, *, scope: str, message: str) -> None:
    """최근 오류를 기록한다."""

    with service._lock:
        append_error(service._state, scope=scope, message=message)
