"""StreamAlignmentManager 동작 테스트."""

from __future__ import annotations

from backend.app.services.audio.pipeline.stream_alignment_manager import StreamAlignmentManager


class TestStreamAlignmentManager:
    """segment 정합성과 backpressure 상태 관리를 검증한다."""

    def test_threshold_미만이면_backpressure를_활성화하지_않는다(self) -> None:
        manager = StreamAlignmentManager(
            preview_backpressure_queue_delay_ms=1500,
            preview_backpressure_hold_chunks=4,
        )

        activated, hold_chunks = manager.apply_final_queue_delay(1499)

        assert activated is False
        assert hold_chunks == 0

    def test_threshold_이상이면_기본_hold_chunks를_활성화한다(self) -> None:
        manager = StreamAlignmentManager(
            preview_backpressure_queue_delay_ms=1500,
            preview_backpressure_hold_chunks=4,
        )

        activated, hold_chunks = manager.apply_final_queue_delay(1500)

        assert activated is True
        assert hold_chunks == 4

    def test_queue_delay가_커져도_hold_chunks는_기본값을_유지한다(self) -> None:
        manager = StreamAlignmentManager(
            preview_backpressure_queue_delay_ms=1500,
            preview_backpressure_hold_chunks=4,
        )

        activated, hold_chunks = manager.apply_final_queue_delay(10_000)

        assert activated is True
        assert hold_chunks == 4

    def test_tick_preview_backpressure가_남은_청크를_감소시킨다(self) -> None:
        manager = StreamAlignmentManager(
            preview_backpressure_queue_delay_ms=1500,
            preview_backpressure_hold_chunks=4,
        )
        manager.apply_final_queue_delay(10_000)

        suppressed, remaining = manager.tick_preview_backpressure()

        assert suppressed is True
        assert remaining == 3

    def test_clear_preview_backpressure가_남은_억제를_초기화한다(self) -> None:
        manager = StreamAlignmentManager(
            preview_backpressure_queue_delay_ms=1500,
            preview_backpressure_hold_chunks=4,
        )
        manager.apply_final_queue_delay(10_000)

        manager.clear_preview_backpressure()
        suppressed, remaining = manager.tick_preview_backpressure()

        assert suppressed is False
        assert remaining == 0
