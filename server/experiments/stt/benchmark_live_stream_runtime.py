"""실시간 런타임의 멀티세션 부하를 합성 워크로드로 측정한다."""

from __future__ import annotations

import argparse
import asyncio
import json
import statistics
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[3]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from server.app.services.audio.runtime.live_stream_service import LiveStreamService  # noqa: E402


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="live stream runtime synthetic 부하를 측정합니다.")
    parser.add_argument("--sessions", default="1,2,4,8", help="동시 세션 수 목록 (쉼표 구분)")
    parser.add_argument("--workers", default="1,2", help="worker 수 목록 (쉼표 구분)")
    parser.add_argument("--chunks-per-session", type=int, default=10, help="세션당 청크 수")
    parser.add_argument("--chunk-interval-ms", type=int, default=20, help="청크 전송 간격(ms)")
    parser.add_argument("--preview-latency-ms", type=int, default=8, help="preview 처리 지연(ms)")
    parser.add_argument("--final-latency-ms", type=int, default=60, help="final 처리 지연(ms)")
    parser.add_argument("--pending-per-stream", type=int, default=3, help="스트림당 pending final 큐 길이")
    parser.add_argument("--max-running-streams", type=int, default=16, help="동시 실행 가능한 최대 stream 수")
    parser.add_argument("--sample-interval-ms", type=int, default=10, help="runtime snapshot 샘플링 간격(ms)")
    parser.add_argument("--output-json", help="결과 JSON 저장 경로")
    return parser


@dataclass
class ScenarioResult:
    workers: int
    sessions: int
    chunks_per_session: int
    chunk_interval_ms: int
    preview_latency_ms: int
    final_latency_ms: int
    elapsed_seconds: float
    total_tokens: int
    preview_token_count: int
    final_token_count: int
    preview_delivery_rate: float
    final_delivery_rate: float
    preview_p50_ms: float | None
    preview_p95_ms: float | None
    final_p50_ms: float | None
    final_p95_ms: float | None
    max_pending_chunk_count: int
    max_busy_stream_count: int
    max_draining_stream_count: int
    coalesced_chunk_count: int
    busy_worker_count_peak: int


@dataclass
class RuntimeSnapshotStats:
    max_pending_chunk_count: int = 0
    max_busy_stream_count: int = 0
    max_draining_stream_count: int = 0
    busy_worker_count_peak: int = 0
    coalesced_chunk_count: int = 0

    def observe(self, snapshot: dict[str, object]) -> None:
        self.max_pending_chunk_count = max(
            self.max_pending_chunk_count,
            int(snapshot.get("pending_chunk_count", 0)),
        )
        self.max_busy_stream_count = max(
            self.max_busy_stream_count,
            int(snapshot.get("busy_stream_count", 0)),
        )
        self.max_draining_stream_count = max(
            self.max_draining_stream_count,
            int(snapshot.get("draining_stream_count", 0)),
        )
        self.busy_worker_count_peak = max(
            self.busy_worker_count_peak,
            int(snapshot.get("busy_worker_count", 0)),
        )
        self.coalesced_chunk_count = max(
            self.coalesced_chunk_count,
            int(snapshot.get("coalesced_chunk_count", 0)),
        )


class SyntheticPreviewFinalPipeline:
    """preview/final 경로를 분리한 합성 파이프라인."""

    def __init__(self, *, preview_latency_ms: int, final_latency_ms: int) -> None:
        self._preview_latency_seconds = max(preview_latency_ms, 0) / 1000.0
        self._final_latency_seconds = max(final_latency_ms, 0) / 1000.0

    def supports_preview(self) -> bool:
        return True

    def process_preview_chunk(self, session_id: str, chunk: bytes, input_source: str | None):
        time.sleep(self._preview_latency_seconds)
        text = chunk.decode("utf-8").strip()
        if not text:
            return []
        return [f"preview:{text}"]

    def process_final_chunk(self, session_id: str, chunk: bytes, input_source: str | None):
        time.sleep(self._final_latency_seconds)
        text = chunk.decode("utf-8").strip()
        if not text:
            return [], []
        return [f"final:{text}"], []


async def benchmark_scenario(
    *,
    workers: int,
    sessions: int,
    chunks_per_session: int,
    chunk_interval_ms: int,
    preview_latency_ms: int,
    final_latency_ms: int,
    pending_per_stream: int,
    max_running_streams: int,
    sample_interval_ms: int,
) -> ScenarioResult:
    service = LiveStreamService(
        worker_count=workers,
        pending_chunks_per_stream=pending_per_stream,
        max_running_streams=max(max_running_streams, sessions),
    )
    await service.start()

    token_sent_at: dict[str, float] = {}
    preview_latencies_ms: list[float] = []
    final_latencies_ms: list[float] = []
    snapshot_stats = RuntimeSnapshotStats()
    stop_sampling = asyncio.Event()
    context_ids: list[str] = []

    async def sample_runtime() -> None:
        while not stop_sampling.is_set():
            snapshot_stats.observe(service.build_snapshot())
            await asyncio.sleep(max(sample_interval_ms, 1) / 1000.0)
        snapshot_stats.observe(service.build_snapshot())

    async def produce(session_index: int, context_id: str) -> None:
        for chunk_index in range(chunks_per_session):
            token = f"s{session_index}-c{chunk_index}"
            token_sent_at[token] = time.perf_counter()
            await service.enqueue_chunk(context_id, token.encode("utf-8"))
            await asyncio.sleep(max(chunk_interval_ms, 0) / 1000.0)
        await service.close_input(context_id)

    async def consume(context_id: str) -> None:
        while True:
            result = await service.receive_result(context_id)
            received_at = time.perf_counter()
            if result.terminal:
                return
            for utterance in result.utterances:
                if not isinstance(utterance, str) or ":" not in utterance:
                    continue
                kind, raw_tokens = utterance.split(":", 1)
                for token in [value for value in raw_tokens.split() if value]:
                    sent_at = token_sent_at.get(token)
                    if sent_at is None:
                        continue
                    latency_ms = (received_at - sent_at) * 1000.0
                    if kind == "preview":
                        preview_latencies_ms.append(latency_ms)
                    elif kind == "final":
                        final_latencies_ms.append(latency_ms)

    sampling_task = asyncio.create_task(sample_runtime(), name="runtime-benchmark-sampler")
    started_at = time.perf_counter()
    try:
        for session_index in range(sessions):
            context_id = await service.open_stream(
                session_id=f"benchmark-session-{session_index}",
                input_source="mic",
                stream_kind="text",
                pipeline_service=SyntheticPreviewFinalPipeline(
                    preview_latency_ms=preview_latency_ms,
                    final_latency_ms=final_latency_ms,
                ),
            )
            context_ids.append(context_id)

        producer_tasks = [
            asyncio.create_task(produce(index, context_id), name=f"benchmark-producer-{index}")
            for index, context_id in enumerate(context_ids)
        ]
        consumer_tasks = [
            asyncio.create_task(consume(context_id), name=f"benchmark-consumer-{index}")
            for index, context_id in enumerate(context_ids)
        ]

        await asyncio.gather(*producer_tasks)
        await asyncio.gather(*consumer_tasks)
        elapsed_seconds = time.perf_counter() - started_at
        snapshot_stats.observe(service.build_snapshot())
    finally:
        stop_sampling.set()
        await sampling_task
        for context_id in context_ids:
            await service.close_stream(context_id)
        await service.shutdown()

    total_tokens = sessions * chunks_per_session
    preview_token_count = len(preview_latencies_ms)
    final_token_count = len(final_latencies_ms)

    return ScenarioResult(
        workers=workers,
        sessions=sessions,
        chunks_per_session=chunks_per_session,
        chunk_interval_ms=chunk_interval_ms,
        preview_latency_ms=preview_latency_ms,
        final_latency_ms=final_latency_ms,
        elapsed_seconds=round(elapsed_seconds, 4),
        total_tokens=total_tokens,
        preview_token_count=preview_token_count,
        final_token_count=final_token_count,
        preview_delivery_rate=round(preview_token_count / total_tokens, 4) if total_tokens else 0.0,
        final_delivery_rate=round(final_token_count / total_tokens, 4) if total_tokens else 0.0,
        preview_p50_ms=_percentile(preview_latencies_ms, 50),
        preview_p95_ms=_percentile(preview_latencies_ms, 95),
        final_p50_ms=_percentile(final_latencies_ms, 50),
        final_p95_ms=_percentile(final_latencies_ms, 95),
        max_pending_chunk_count=snapshot_stats.max_pending_chunk_count,
        max_busy_stream_count=snapshot_stats.max_busy_stream_count,
        max_draining_stream_count=snapshot_stats.max_draining_stream_count,
        coalesced_chunk_count=snapshot_stats.coalesced_chunk_count,
        busy_worker_count_peak=snapshot_stats.busy_worker_count_peak,
    )


def _parse_int_list(raw_value: str) -> list[int]:
    values = []
    for token in raw_value.split(","):
        token = token.strip()
        if not token:
            continue
        values.append(int(token))
    return values


def _percentile(values: list[float], percentile: int) -> float | None:
    if not values:
        return None
    if len(values) == 1:
        return round(values[0], 2)
    quantiles = statistics.quantiles(values, n=100, method="inclusive")
    return round(quantiles[percentile - 1], 2)


def print_summary(results: list[ScenarioResult]) -> None:
    print(
        "workers sessions elapsed_s preview_p50 preview_p95 final_p50 final_p95 "
        "preview_rate final_rate max_pending coalesced busy_workers"
    )
    for item in results:
        print(
            f"{item.workers:>7} {item.sessions:>8} {item.elapsed_seconds:>8.2f} "
            f"{_fmt(item.preview_p50_ms):>11} {_fmt(item.preview_p95_ms):>11} "
            f"{_fmt(item.final_p50_ms):>9} {_fmt(item.final_p95_ms):>9} "
            f"{item.preview_delivery_rate:>12.2%} {item.final_delivery_rate:>10.2%} "
            f"{item.max_pending_chunk_count:>11} {item.coalesced_chunk_count:>9} "
            f"{item.busy_worker_count_peak:>12}"
        )


def _fmt(value: float | None) -> str:
    if value is None:
        return "-"
    return f"{value:.2f}"


async def async_main(args: argparse.Namespace) -> list[ScenarioResult]:
    worker_values = _parse_int_list(args.workers)
    session_values = _parse_int_list(args.sessions)
    results: list[ScenarioResult] = []
    for worker_count in worker_values:
        for session_count in session_values:
            result = await benchmark_scenario(
                workers=worker_count,
                sessions=session_count,
                chunks_per_session=args.chunks_per_session,
                chunk_interval_ms=args.chunk_interval_ms,
                preview_latency_ms=args.preview_latency_ms,
                final_latency_ms=args.final_latency_ms,
                pending_per_stream=args.pending_per_stream,
                max_running_streams=args.max_running_streams,
                sample_interval_ms=args.sample_interval_ms,
            )
            results.append(result)
    return results


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    results = asyncio.run(async_main(args))
    print_summary(results)
    if args.output_json:
        output_path = Path(args.output_json).resolve()
        payload = [result.__dict__ for result in results]
        output_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"saved_json={output_path}")


if __name__ == "__main__":
    main()
