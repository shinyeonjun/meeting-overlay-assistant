"""오디오 영역의 stream alignment manager 서비스를 제공한다."""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class AlignmentCounters:
    """정합성 카운터 스냅샷."""

    matched: int
    grace_matched: int
    standalone: int
    standalone_ratio: float


class StreamAlignmentManager:
    """partial/final 세그먼트 정합성 및 backpressure 상태를 관리한다."""

    def __init__(
        self,
        *,
        preview_backpressure_queue_delay_ms: int = 0,
        preview_backpressure_hold_chunks: int = 0,
        segment_grace_match_max_gap_ms: int = 0,
    ) -> None:
        self._preview_backpressure_queue_delay_ms = preview_backpressure_queue_delay_ms
        self._preview_backpressure_hold_chunks = preview_backpressure_hold_chunks
        self._segment_grace_match_max_gap_ms = segment_grace_match_max_gap_ms

        self._preview_seq_num = 0
        self._segment_counter = 0

        self._active_preview_seq_num: int | None = None
        self._active_preview_segment_id: str | None = None
        self._recent_preview_seq_num: int | None = None
        self._recent_preview_segment_id: str | None = None
        self._recent_preview_seen_at_ms: int | None = None
        self._recent_consumed_segment_id: str | None = None

        self._preview_backpressure_remaining_chunks = 0

        self._alignment_matched_count = 0
        self._alignment_grace_matched_count = 0
        self._alignment_standalone_count = 0

    def tick_preview_backpressure(self) -> tuple[bool, int]:
        """preview 억제 필요 여부를 반환하고 카운터를 1 감소시킨다."""
        if self._preview_backpressure_remaining_chunks <= 0:
            return False, 0
        self._preview_backpressure_remaining_chunks -= 1
        return True, self._preview_backpressure_remaining_chunks

    def clear_preview_backpressure(self) -> None:
        """preview backpressure를 즉시 해제한다."""
        self._preview_backpressure_remaining_chunks = 0

    def apply_final_queue_delay(self, final_queue_delay_ms: int) -> tuple[bool, int]:
        """final 큐 지연이 크면 preview backpressure를 활성화한다."""
        if self._preview_backpressure_queue_delay_ms <= 0:
            return False, self._preview_backpressure_remaining_chunks
        if final_queue_delay_ms < self._preview_backpressure_queue_delay_ms:
            return False, self._preview_backpressure_remaining_chunks

        base_hold_chunks = max(self._preview_backpressure_hold_chunks, 0)
        if base_hold_chunks == 0:
            return False, self._preview_backpressure_remaining_chunks

        self._preview_backpressure_remaining_chunks = max(
            self._preview_backpressure_remaining_chunks,
            base_hold_chunks,
        )
        return True, self._preview_backpressure_remaining_chunks

    def get_or_create_preview_binding(self) -> tuple[int, str]:
        """현재 active preview 바인딩을 반환하고, 없으면 새로 생성한다."""
        if self._active_preview_seq_num is None:
            self._preview_seq_num += 1
            self._active_preview_seq_num = self._preview_seq_num
        if self._active_preview_segment_id is None:
            self._active_preview_segment_id = self._next_segment_id()
        return self._active_preview_seq_num, self._active_preview_segment_id

    def mark_preview_emitted(self, *, seq_num: int, segment_id: str, now_ms: int) -> None:
        """preview 전송 후 active/recent 상태를 갱신한다."""
        self._active_preview_seq_num = seq_num
        self._active_preview_segment_id = segment_id
        self._recent_preview_seq_num = seq_num
        self._recent_preview_segment_id = segment_id
        self._recent_preview_seen_at_ms = now_ms

    def consume_for_final(self, *, now_ms: int, start_ms: int, end_ms: int) -> tuple[str, int | None, str]:
        """final 결과를 어떤 segment 바인딩으로 보낼지 결정한다."""
        if self._active_preview_segment_id is not None:
            segment_id = self._active_preview_segment_id
            seq_num = self._active_preview_seq_num
            self._active_preview_segment_id = None
            self._active_preview_seq_num = None
            self._recent_consumed_segment_id = segment_id
            return segment_id, seq_num, "matched_active_preview"

        if self._should_grace_match_recent_preview(now_ms):
            segment_id = self._recent_preview_segment_id
            seq_num = self._recent_preview_seq_num
            self._recent_consumed_segment_id = segment_id
            return segment_id, seq_num, "grace_matched_recent_preview"

        return self._segment_id_from_times(start_ms, end_ms), None, "standalone_final"

    def record_alignment(self, alignment_status: str) -> AlignmentCounters:
        """정합성 상태를 누적하고 스냅샷을 반환한다."""
        if alignment_status == "matched_active_preview":
            self._alignment_matched_count += 1
        elif alignment_status == "grace_matched_recent_preview":
            self._alignment_grace_matched_count += 1
        else:
            self._alignment_standalone_count += 1

        total = (
            self._alignment_matched_count
            + self._alignment_grace_matched_count
            + self._alignment_standalone_count
        )
        standalone_ratio = (self._alignment_standalone_count / total) if total else 0.0
        return AlignmentCounters(
            matched=self._alignment_matched_count,
            grace_matched=self._alignment_grace_matched_count,
            standalone=self._alignment_standalone_count,
            standalone_ratio=standalone_ratio,
        )

    def clear_active_preview(self) -> None:
        """현재 active preview 바인딩만 초기화한다."""
        self._active_preview_seq_num = None
        self._active_preview_segment_id = None

    def prime_recent_preview_for_test(
        self,
        *,
        seq_num: int,
        segment_id: str,
        seen_at_ms: int,
        consumed_segment_id: str | None = None,
    ) -> None:
        """테스트에서 최근 preview 상태를 직접 주입할 때 사용한다."""
        self._recent_preview_seq_num = seq_num
        self._recent_preview_segment_id = segment_id
        self._recent_preview_seen_at_ms = seen_at_ms
        self._recent_consumed_segment_id = consumed_segment_id

    def _should_grace_match_recent_preview(self, now_ms: int) -> bool:
        if self._segment_grace_match_max_gap_ms <= 0:
            return False
        if self._recent_preview_segment_id is None or self._recent_preview_seq_num is None:
            return False
        if self._recent_preview_seen_at_ms is None:
            return False
        if self._recent_preview_segment_id == self._recent_consumed_segment_id:
            return False
        return (now_ms - self._recent_preview_seen_at_ms) <= self._segment_grace_match_max_gap_ms

    def _next_segment_id(self) -> str:
        self._segment_counter += 1
        return f"seg-live-{self._segment_counter}"

    @staticmethod
    def _segment_id_from_times(start_ms: int, end_ms: int) -> str:
        return f"seg-{start_ms}-{end_ms}"
