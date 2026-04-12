"""벤치마크 계산 유틸리티 테스트."""

from server.app.services.audio.stt.benchmarking import (
    GuardPassStats,
    compute_character_error_rate,
    compute_word_error_rate,
)


class TestBenchmarking:
    """벤치마크 계산 유틸리티를 검증한다."""

    def test_word_error_rate를_계산한다(self):
        result = compute_word_error_rate(
            "안녕하세요 회의를 시작합니다",
            "안녕하세요 회의 시작합니다",
        )

        assert result.distance == 1
        assert result.reference_length == 3
        assert result.rate == 0.3333

    def test_character_error_rate를_계산한다(self):
        result = compute_character_error_rate("안녕하세요", "안녕하새요")

        assert result.distance == 1
        assert result.reference_length == 5
        assert result.rate == 0.2

    def test_guard_pass_stats가_비율을_계산한다(self):
        stats = GuardPassStats(
            raw_segment_count=10,
            non_empty_segment_count=6,
            kept_segment_count=4,
        )

        assert stats.non_empty_rate == 0.6
        assert stats.keep_rate_vs_raw == 0.4
        assert stats.keep_rate_vs_non_empty == 4 / 6

