"""세션별 preview cycle 기록 저장소."""

from __future__ import annotations

from collections import deque


class PreviewCycleStore:
    """preview cycle 기록을 세션 단위로 보관한다."""

    def __init__(self, *, window_size: int) -> None:
        self._window_size = window_size
        self.reset()

    def reset(self) -> None:
        """저장된 preview cycle 기록을 모두 초기화한다."""

        self._cycles_by_session: dict[str, dict[int, dict[str, object]]] = {}
        self._cycle_order_by_session: dict[str, deque[int]] = {}

    def get_record(
        self,
        *,
        session_id: str,
        preview_cycle_id: int,
        recorded_at_epoch_ms: int,
    ) -> dict[str, object]:
        """preview cycle 레코드를 반환하고, 없으면 새로 만든다."""

        cycles = self._cycles_by_session.setdefault(session_id, {})
        existing = cycles.get(preview_cycle_id)
        if existing is not None:
            anchor_epoch_ms = existing.get("anchor_epoch_ms")
            if not isinstance(anchor_epoch_ms, int) or recorded_at_epoch_ms < anchor_epoch_ms:
                existing["anchor_epoch_ms"] = recorded_at_epoch_ms
            return existing

        record = {
            "preview_cycle_id": preview_cycle_id,
            "anchor_epoch_ms": recorded_at_epoch_ms,
            "ready_at_epoch_ms": None,
            "picked_at_epoch_ms": None,
            "job_started_at_epoch_ms": None,
            "sherpa_non_empty_at_epoch_ms": None,
            "candidate_at_epoch_ms": None,
            "emitted_at_epoch_ms": None,
            "ready_pending_final_chunk_count": None,
            "ready_busy_worker_count": None,
            "picked_pending_final_chunk_count": None,
            "picked_busy_worker_count": None,
        }
        cycles[preview_cycle_id] = record
        order = self._cycle_order_by_session.setdefault(
            session_id,
            deque(maxlen=self._window_size),
        )
        if len(order) == order.maxlen and order:
            cycles.pop(order[0], None)
        order.append(preview_cycle_id)
        return record

    def list_cycles(self) -> list[dict[str, object]]:
        """모든 session preview cycle을 평탄화해서 반환한다."""

        return [
            {"session_id": session_id, **cycle}
            for session_id, cycles in self._cycles_by_session.items()
            for cycle in cycles.values()
        ]

    @staticmethod
    def assign_first_epoch_ms(
        record: dict[str, object],
        key: str,
        recorded_at_epoch_ms: int,
    ) -> None:
        """더 이른 epoch 값만 유지한다."""

        current = record.get(key)
        if not isinstance(current, int) or recorded_at_epoch_ms < current:
            record[key] = recorded_at_epoch_ms
