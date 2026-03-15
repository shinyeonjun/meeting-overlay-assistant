"""서버 런타임 모니터링 상태를 메모리에서 수집한다."""

from __future__ import annotations

from collections import deque
from datetime import datetime, timezone
from threading import Lock


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class RuntimeMonitorService:
    """실시간 처리 지표를 최근 윈도우 기준으로 집계한다."""

    def __init__(
        self,
        *,
        final_window_size: int = 120,
        chunk_window_size: int = 120,
        rejection_window_size: int = 120,
        backpressure_window_size: int = 120,
        error_window_size: int = 40,
    ) -> None:
        self._lock = Lock()
        self._final_window_size = final_window_size
        self._chunk_window_size = chunk_window_size
        self._rejection_window_size = rejection_window_size
        self._backpressure_window_size = backpressure_window_size
        self._error_window_size = error_window_size
        self.reset()

    def reset(self) -> None:
        """누적된 모니터링 상태를 초기화한다."""

        with self._lock:
            self._recent_finals: deque[dict[str, object]] = deque(maxlen=self._final_window_size)
            self._recent_chunks: deque[dict[str, object]] = deque(maxlen=self._chunk_window_size)
            self._recent_rejections: deque[dict[str, object]] = deque(maxlen=self._rejection_window_size)
            self._recent_backpressure: deque[dict[str, object]] = deque(maxlen=self._backpressure_window_size)
            self._recent_errors: deque[dict[str, object]] = deque(maxlen=self._error_window_size)
            self._last_chunk_processed_at: str | None = None
            self._last_error_at: str | None = None
            self._last_error_message: str | None = None

    def record_final_transcription(
        self,
        *,
        session_id: str,
        final_queue_delay_ms: int,
        emitted_live_final: bool,
        alignment_status: str,
    ) -> None:
        """최종 전사 결과와 지연 상태를 기록한다."""

        with self._lock:
            self._recent_finals.append(
                {
                    "session_id": session_id,
                    "final_queue_delay_ms": final_queue_delay_ms,
                    "emitted_live_final": emitted_live_final,
                    "alignment_status": alignment_status,
                    "recorded_at": _utc_now_iso(),
                }
            )

    def record_preview_backpressure(
        self,
        *,
        final_queue_delay_ms: int,
        hold_chunks: int,
    ) -> None:
        """preview backpressure 활성화를 기록한다."""

        with self._lock:
            self._recent_backpressure.append(
                {
                    "final_queue_delay_ms": final_queue_delay_ms,
                    "hold_chunks": hold_chunks,
                    "recorded_at": _utc_now_iso(),
                }
            )

    def record_rejection(self, *, reason: str | None) -> None:
        """전사 필터링 사유를 기록한다."""

        with self._lock:
            self._recent_rejections.append(
                {
                    "reason": reason or "unknown",
                    "recorded_at": _utc_now_iso(),
                }
            )

    def record_chunk_processed(
        self,
        *,
        session_id: str,
        utterance_count: int,
        event_count: int,
    ) -> None:
        """chunk 처리 결과를 기록한다."""

        processed_at = _utc_now_iso()
        with self._lock:
            self._recent_chunks.append(
                {
                    "session_id": session_id,
                    "utterance_count": utterance_count,
                    "event_count": event_count,
                    "processed_at": processed_at,
                }
            )
            self._last_chunk_processed_at = processed_at

    def record_error(self, *, scope: str, message: str) -> None:
        """최근 오류를 기록한다."""

        recorded_at = _utc_now_iso()
        with self._lock:
            self._recent_errors.append(
                {
                    "scope": scope,
                    "message": message,
                    "recorded_at": recorded_at,
                }
            )
            self._last_error_at = recorded_at
            self._last_error_message = f"{scope}: {message}"

    def build_snapshot(self) -> dict[str, object]:
        """현재 모니터링 상태를 API 응답용 dict로 반환한다."""

        with self._lock:
            finals = list(self._recent_finals)
            chunks = list(self._recent_chunks)
            rejections = list(self._recent_rejections)
            backpressure = list(self._recent_backpressure)
            errors = list(self._recent_errors)
            last_chunk_processed_at = self._last_chunk_processed_at
            last_error_at = self._last_error_at
            last_error_message = self._last_error_message

        queue_delays = [
            int(item["final_queue_delay_ms"])
            for item in finals
            if isinstance(item.get("final_queue_delay_ms"), int)
        ]
        recent_utterance_count = sum(
            int(item["utterance_count"])
            for item in chunks
            if isinstance(item.get("utterance_count"), int)
        )
        recent_event_count = sum(
            int(item["event_count"])
            for item in chunks
            if isinstance(item.get("event_count"), int)
        )
        matched_count = sum(1 for item in finals if item.get("alignment_status") == "matched")
        grace_matched_count = sum(
            1 for item in finals if item.get("alignment_status") == "grace_matched"
        )
        standalone_count = sum(1 for item in finals if item.get("alignment_status") == "standalone_final")
        final_count = len(finals)

        return {
            "generated_at": _utc_now_iso(),
            "audio_pipeline": {
                "recent_final_count": final_count,
                "recent_utterance_count": recent_utterance_count,
                "recent_event_count": recent_event_count,
                "average_queue_delay_ms": (
                    round(sum(queue_delays) / len(queue_delays), 1) if queue_delays else None
                ),
                "max_queue_delay_ms": max(queue_delays) if queue_delays else None,
                "late_final_count": sum(
                    1 for item in finals if item.get("emitted_live_final") is False
                ),
                "backpressure_count": len(backpressure),
                "filtered_count": len(rejections),
                "error_count": len(errors),
                "matched_count": matched_count,
                "grace_matched_count": grace_matched_count,
                "standalone_count": standalone_count,
                "standalone_ratio": (
                    round(standalone_count / final_count, 2) if final_count else 0.0
                ),
                "last_chunk_processed_at": last_chunk_processed_at,
                "last_error_at": last_error_at,
                "last_error_message": last_error_message,
            },
        }
