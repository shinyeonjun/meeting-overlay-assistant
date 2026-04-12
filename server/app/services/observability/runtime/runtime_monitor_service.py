"""공통 영역의 runtime monitor service 서비스를 제공한다."""
from __future__ import annotations

from threading import Lock

from server.app.services.observability.runtime.service_helpers import (
    build_snapshot,
    get_preview_cycle_record,
    record_chunk_processed,
    record_error,
    record_final_transcription,
    record_preview_backpressure,
    record_preview_candidate,
    record_preview_emitted,
    record_preview_rejection,
    record_preview_skip,
    record_preview_stage,
    record_rejection,
    reset_state,
)


class RuntimeMonitorService:
    """실시간 처리 지표를 최근 윈도우 기준으로 집계한다."""

    def __init__(
        self,
        *,
        final_window_size: int = 120,
        preview_window_size: int = 240,
        chunk_window_size: int = 120,
        rejection_window_size: int = 120,
        backpressure_window_size: int = 120,
        error_window_size: int = 40,
    ) -> None:
        self._lock = Lock()
        self._final_window_size = final_window_size
        self._preview_window_size = preview_window_size
        self._chunk_window_size = chunk_window_size
        self._rejection_window_size = rejection_window_size
        self._backpressure_window_size = backpressure_window_size
        self._error_window_size = error_window_size
        self.reset()

    def reset(self) -> None:
        """추적 중인 모니터 상태를 초기화한다."""

        reset_state(self)

    def _get_preview_cycle_record(
        self,
        *,
        session_id: str,
        preview_cycle_id: int,
        recorded_at_epoch_ms: int,
    ) -> dict[str, object]:
        """세션별 preview cycle 레코드를 반환한다."""

        return get_preview_cycle_record(
            self,
            session_id=session_id,
            preview_cycle_id=preview_cycle_id,
            recorded_at_epoch_ms=recorded_at_epoch_ms,
        )

    def record_final_transcription(
        self,
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

        record_final_transcription(
            self,
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
        self,
        *,
        session_id: str,
        kind: str,
        preview_cycle_id: int | None = None,
    ) -> None:
        """preview/live_final 후보가 생성됐다는 사실을 기록한다."""

        record_preview_candidate(
            self,
            session_id=session_id,
            kind=kind,
            preview_cycle_id=preview_cycle_id,
        )

    def record_preview_emitted(
        self,
        *,
        session_id: str,
        kind: str,
        preview_cycle_id: int | None = None,
    ) -> None:
        """preview/live_final이 실제 payload로 전송됐다는 사실을 기록한다."""

        record_preview_emitted(
            self,
            session_id=session_id,
            kind=kind,
            preview_cycle_id=preview_cycle_id,
        )

    def record_preview_stage(
        self,
        *,
        session_id: str,
        stage: str,
        pending_final_chunk_count: int | None = None,
        busy_worker_count: int | None = None,
        preview_cycle_id: int | None = None,
    ) -> None:
        """preview 처리 단계 타임스탬프를 기록한다."""

        record_preview_stage(
            self,
            session_id=session_id,
            stage=stage,
            pending_final_chunk_count=pending_final_chunk_count,
            busy_worker_count=busy_worker_count,
            preview_cycle_id=preview_cycle_id,
        )

    def record_preview_skip(
        self,
        *,
        session_id: str,
        reason: str,
        pending_final_chunk_count: int | None,
        has_pending_preview_chunk: bool | None,
        busy_worker_count: int | None,
        busy_job_kind: str | None,
    ) -> None:
        """preview ready/pick 이전의 스케줄링 단계에서 건너뛴 사유를 기록한다."""

        record_preview_skip(
            self,
            session_id=session_id,
            reason=reason,
            pending_final_chunk_count=pending_final_chunk_count,
            has_pending_preview_chunk=has_pending_preview_chunk,
            busy_worker_count=busy_worker_count,
            busy_job_kind=busy_job_kind,
        )

    def record_preview_rejection(
        self,
        *,
        session_id: str,
        reason: str | None,
        filter_stage: str,
    ) -> None:
        """preview 후보가 필터에서 탈락했다는 사실을 기록한다."""

        record_preview_rejection(
            self,
            session_id=session_id,
            reason=reason,
            filter_stage=filter_stage,
        )

    def record_preview_backpressure(
        self,
        *,
        session_id: str | None = None,
        final_queue_delay_ms: int,
        hold_chunks: int,
    ) -> None:
        """preview backpressure 발생을 기록한다."""

        record_preview_backpressure(
            self,
            session_id=session_id,
            final_queue_delay_ms=final_queue_delay_ms,
            hold_chunks=hold_chunks,
        )

    def record_rejection(self, *, reason: str | None) -> None:
        """전사 필터 사유를 기록한다."""

        record_rejection(self, reason=reason)

    def record_chunk_processed(
        self,
        *,
        session_id: str,
        utterance_count: int,
        event_count: int,
    ) -> None:
        """chunk 처리 결과를 기록한다."""

        record_chunk_processed(
            self,
            session_id=session_id,
            utterance_count=utterance_count,
            event_count=event_count,
        )

    def record_error(self, *, scope: str, message: str) -> None:
        """최근 오류를 기록한다."""

        record_error(self, scope=scope, message=message)

    def build_snapshot(self, *, session_id: str | None = None) -> dict[str, object]:
        """현재 모니터 상태를 API 응답용 dict로 반환한다."""

        return build_snapshot(self, session_id=session_id)
