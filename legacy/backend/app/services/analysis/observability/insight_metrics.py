"""인사이트 추출 파이프라인 메트릭 집계."""

from __future__ import annotations

from collections import Counter
from threading import Lock


class _InsightMetrics:
    """프로세스 내 인사이트 메트릭을 집계한다."""

    def __init__(self) -> None:
        self._lock = Lock()
        self._counters: Counter[str] = Counter()

    def increment(self, metric_key: str, amount: int = 1) -> None:
        if amount <= 0:
            return
        with self._lock:
            self._counters[metric_key] += amount

    def snapshot(self) -> dict[str, int]:
        with self._lock:
            return dict(self._counters)


_INSIGHT_METRICS = _InsightMetrics()


def record_insight_provider_invocation(backend_name: str) -> None:
    backend = (backend_name or "unknown").strip() or "unknown"
    _INSIGHT_METRICS.increment("insight.provider.calls_total")
    _INSIGHT_METRICS.increment(f"insight.provider.calls_total.by_backend.{backend}")


def record_insight_provider_exception(backend_name: str, error_type: str) -> None:
    backend = (backend_name or "unknown").strip() or "unknown"
    normalized_error = (error_type or "unknown").strip() or "unknown"
    _INSIGHT_METRICS.increment("insight.provider.errors_total")
    _INSIGHT_METRICS.increment(f"insight.provider.errors_total.by_backend.{backend}")
    _INSIGHT_METRICS.increment(
        f"insight.provider.errors_total.by_type.{normalized_error}"
    )


def record_insight_parse_failure(reason: str) -> None:
    normalized_reason = (reason or "unknown").strip() or "unknown"
    _INSIGHT_METRICS.increment("insight.parser.failures_total")
    _INSIGHT_METRICS.increment(
        f"insight.parser.failures_total.by_reason.{normalized_reason}"
    )


def record_insight_candidate_dropped(reason: str) -> None:
    normalized_reason = (reason or "unknown").strip() or "unknown"
    _INSIGHT_METRICS.increment("insight.candidate.dropped_total")
    _INSIGHT_METRICS.increment(
        f"insight.candidate.dropped_total.by_reason.{normalized_reason}"
    )


def record_insight_candidates_emitted(count: int) -> None:
    _INSIGHT_METRICS.increment("insight.candidate.emitted_total", max(count, 0))


def get_insight_metrics_snapshot() -> dict[str, int]:
    """현재까지 집계된 인사이트 메트릭 스냅샷을 반환한다."""
    return _INSIGHT_METRICS.snapshot()
