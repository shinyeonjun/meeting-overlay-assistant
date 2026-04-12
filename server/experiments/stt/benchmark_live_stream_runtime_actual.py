"""실제 STT backend를 붙인 live runtime 부하 테스트 스크립트."""

from __future__ import annotations

import argparse
import asyncio
import json
import statistics
import sys
import time
from dataclasses import asdict, dataclass
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[3]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from server.app.api.http import dependencies as dependency_module  # noqa: E402
from server.app.api.http.wiring import audio_runtime  # noqa: E402
from server.app.core.audio_source_policy import resolve_audio_source_policy  # noqa: E402
from server.app.core.config import settings  # noqa: E402
from server.app.core.media_service_profiles import resolve_speech_to_text_profile  # noqa: E402
from server.app.services.audio.io.wav_chunk_reader import (  # noqa: E402
    read_pcm_wave_file,
    split_pcm_bytes,
)
from server.app.services.audio.pipeline.audio_pipeline_service import AudioPipelineService  # noqa: E402
from server.app.services.audio.runtime.live_stream_service import LiveStreamService  # noqa: E402
from server.app.services.events.meeting_event_service import MeetingEventService  # noqa: E402


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="현재 settings 기반 실제 STT backend로 live runtime 부하를 측정합니다."
    )
    parser.add_argument(
        "--wav",
        default="tests/fixtures/video/test_16k_mono_15s.wav",
        help="입력 WAV 파일 경로",
    )
    parser.add_argument(
        "--source",
        default="mic",
        choices=["mic", "system_audio"],
        help="측정할 입력 소스",
    )
    parser.add_argument(
        "--sessions",
        default="1,2",
        help="동시 세션 수 목록. 쉼표로 구분",
    )
    parser.add_argument(
        "--workers",
        default="1,2",
        help="worker 수 목록. 쉼표로 구분",
    )
    parser.add_argument(
        "--chunk-ms",
        type=int,
        default=250,
        help="WAV를 나눌 chunk 길이(ms)",
    )
    parser.add_argument(
        "--chunk-interval-ms",
        type=int,
        default=40,
        help="각 chunk를 enqueue하는 간격(ms)",
    )
    parser.add_argument(
        "--pending-per-stream",
        type=int,
        default=3,
        help="스트림별 pending final queue 길이",
    )
    parser.add_argument(
        "--max-running-streams",
        type=int,
        default=8,
        help="동시 실행 가능한 최대 live stream 수",
    )
    parser.add_argument(
        "--sample-interval-ms",
        type=int,
        default=25,
        help="runtime snapshot 샘플링 간격(ms)",
    )
    parser.add_argument(
        "--warmup",
        action="store_true",
        help="본 측정 전 1세션 워밍업을 먼저 수행",
    )
    parser.add_argument(
        "--output-json",
        help="결과 JSON 출력 경로",
    )
    return parser


@dataclass(slots=True)
class SessionMetrics:
    first_preview_latency_ms: float | None = None
    first_final_latency_ms: float | None = None
    terminal_latency_ms: float | None = None
    preview_count: int = 0
    final_count: int = 0
    error_messages: list[str] | None = None


@dataclass(slots=True)
class RuntimeSnapshotStats:
    max_pending_chunk_count: int = 0
    max_busy_stream_count: int = 0
    max_draining_stream_count: int = 0
    coalesced_chunk_count: int = 0
    busy_worker_count_peak: int = 0

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
        self.coalesced_chunk_count = max(
            self.coalesced_chunk_count,
            int(snapshot.get("coalesced_chunk_count", 0)),
        )
        self.busy_worker_count_peak = max(
            self.busy_worker_count_peak,
            int(snapshot.get("busy_worker_count", 0)),
        )


@dataclass(slots=True)
class ScenarioResult:
    source: str
    backend_name: str
    shared_instance: bool
    worker_count: int
    session_count: int
    chunk_ms: int
    chunk_interval_ms: int
    elapsed_seconds: float
    first_preview_p50_ms: float | None
    first_preview_p95_ms: float | None
    first_final_p50_ms: float | None
    first_final_p95_ms: float | None
    terminal_p50_ms: float | None
    terminal_p95_ms: float | None
    preview_emit_count: int
    final_emit_count: int
    errored_session_count: int
    max_pending_chunk_count: int
    max_busy_stream_count: int
    max_draining_stream_count: int
    coalesced_chunk_count: int
    busy_worker_count_peak: int


class _NoOpAnalyzer:
    """실제 backend 지연만 보기 위해 이벤트 분석을 비활성화한다."""

    def analyze(self, utterance):
        return []


class _NoOpUtteranceRepository:
    """duplicate guard에 필요한 최소 인터페이스만 제공한다."""

    def __init__(self) -> None:
        self._seq_by_session: dict[str, int] = {}

    def save(self, utterance, *, connection=None):
        session_id = utterance.session_id
        self._seq_by_session[session_id] = max(
            self._seq_by_session.get(session_id, 0),
            getattr(utterance, "seq_num", 0),
        )
        return utterance

    def next_sequence(self, session_id: str, *, connection=None) -> int:
        next_value = self._seq_by_session.get(session_id, 0) + 1
        self._seq_by_session[session_id] = next_value
        return next_value

    def list_by_session(self, session_id: str, *, connection=None):
        return []

    def list_recent_by_session(self, session_id: str, limit: int, *, connection=None):
        return []


class _NoOpEventRepository:
    """analyzer가 no-op일 때는 호출되지 않지만, service 생성은 가능해야 한다."""

    def save(self, candidate, *, connection=None):
        return candidate

    def update(self, candidate, *, connection=None):
        return candidate

    def delete(self, event_id: str, *, connection=None) -> None:
        return None

    def find_merge_target(self, candidate, *, connection=None):
        return None

    def list_by_source_utterance(self, session_id: str, source_utterance_id: str, insight_scope: str, *, connection=None):
        return []


def _parse_int_list(raw_value: str) -> list[int]:
    values: list[int] = []
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


def _build_actual_pipeline_service(source: str) -> AudioPipelineService:
    source_policy = resolve_audio_source_policy(source, settings)
    return AudioPipelineService(
        segmenter=audio_runtime.build_audio_segmenter(
            source_policy=source_policy,
            settings=settings,
        ),
        speech_to_text_service=dependency_module._get_speech_to_text_service(source),
        analyzer_service=_NoOpAnalyzer(),
        utterance_repository=_NoOpUtteranceRepository(),
        event_service=MeetingEventService(_NoOpEventRepository()),
        transcription_guard=audio_runtime.build_transcription_guard(
            source_policy=source_policy,
            settings=settings,
        ),
        content_gate=audio_runtime.build_audio_content_gate(
            source_policy=source_policy,
            settings=settings,
        ),
        transaction_manager=None,
        runtime_monitor_service=None,
        duplicate_window_ms=source_policy.duplicate_window_ms,
        duplicate_similarity_threshold=source_policy.duplicate_similarity_threshold,
        duplicate_max_confidence=source_policy.duplicate_max_confidence,
        preview_min_compact_length=source_policy.preview_min_compact_length,
        preview_backpressure_queue_delay_ms=source_policy.preview_backpressure_queue_delay_ms,
        preview_backpressure_hold_chunks=source_policy.preview_backpressure_hold_chunks,
        segment_grace_match_max_gap_ms=source_policy.segment_grace_match_max_gap_ms,
        live_final_emit_max_delay_ms=source_policy.live_final_emit_max_delay_ms,
        live_final_initial_grace_segments=source_policy.live_final_initial_grace_segments,
        live_final_initial_grace_delay_ms=source_policy.live_final_initial_grace_delay_ms,
        final_short_text_max_compact_length=source_policy.final_short_text_max_compact_length,
        final_short_text_min_confidence=source_policy.final_short_text_min_confidence,
    )


async def _run_warmup(
    *,
    source: str,
    chunks: list[bytes],
    pending_per_stream: int,
    max_running_streams: int,
) -> None:
    service = LiveStreamService(
        worker_count=1,
        pending_chunks_per_stream=pending_per_stream,
        max_running_streams=max(max_running_streams, 1),
    )
    await service.start()
    try:
        context_id = await service.open_stream(
            session_id="warmup-session",
            input_source=source,
            stream_kind="audio",
            pipeline_service=_build_actual_pipeline_service(source),
        )
        for chunk in chunks[: min(8, len(chunks))]:
            await service.enqueue_chunk(context_id, chunk)
        await service.close_input(context_id)
        while True:
            result = await service.receive_result(context_id)
            if result.terminal:
                break
    finally:
        await service.shutdown()


async def benchmark_scenario(
    *,
    source: str,
    chunks: list[bytes],
    worker_count: int,
    session_count: int,
    chunk_ms: int,
    chunk_interval_ms: int,
    pending_per_stream: int,
    max_running_streams: int,
    sample_interval_ms: int,
) -> ScenarioResult:
    service = LiveStreamService(
        worker_count=worker_count,
        pending_chunks_per_stream=pending_per_stream,
        max_running_streams=max(max_running_streams, session_count),
    )
    await service.start()

    snapshot_stats = RuntimeSnapshotStats()
    stop_sampling = asyncio.Event()
    context_ids: list[str] = []
    session_metrics_by_context: dict[str, SessionMetrics] = {}

    async def sample_runtime() -> None:
        while not stop_sampling.is_set():
            snapshot_stats.observe(service.build_snapshot())
            await asyncio.sleep(max(sample_interval_ms, 1) / 1000.0)
        snapshot_stats.observe(service.build_snapshot())

    async def produce(context_id: str) -> None:
        for chunk in chunks:
            await service.enqueue_chunk(context_id, chunk)
            await asyncio.sleep(max(chunk_interval_ms, 0) / 1000.0)
        await service.close_input(context_id)

    async def consume(context_id: str, started_at: float) -> None:
        metrics = session_metrics_by_context[context_id]
        while True:
            result = await service.receive_result(context_id)
            received_at = time.perf_counter()
            if result.error_message:
                if metrics.error_messages is None:
                    metrics.error_messages = []
                metrics.error_messages.append(result.error_message)
            if result.terminal:
                metrics.terminal_latency_ms = (received_at - started_at) * 1000.0
                return
            for utterance in result.utterances:
                kind = getattr(utterance, "kind", "final")
                if kind == "final":
                    metrics.final_count += 1
                    if metrics.first_final_latency_ms is None:
                        metrics.first_final_latency_ms = (received_at - started_at) * 1000.0
                else:
                    metrics.preview_count += 1
                    if metrics.first_preview_latency_ms is None:
                        metrics.first_preview_latency_ms = (received_at - started_at) * 1000.0

    source_profile = resolve_speech_to_text_profile(dependency_module._resolve_stt_settings_for_source(source))
    sampling_task = asyncio.create_task(sample_runtime(), name="actual-runtime-benchmark-sampler")
    started_at = time.perf_counter()
    try:
        for index in range(session_count):
            context_id = await service.open_stream(
                session_id=f"actual-benchmark-session-{index}",
                input_source=source,
                stream_kind="audio",
                pipeline_service=_build_actual_pipeline_service(source),
            )
            context_ids.append(context_id)
            session_metrics_by_context[context_id] = SessionMetrics()

        producer_tasks = [
            asyncio.create_task(produce(context_id), name=f"actual-benchmark-producer-{index}")
            for index, context_id in enumerate(context_ids)
        ]
        consumer_tasks = [
            asyncio.create_task(consume(context_id, started_at), name=f"actual-benchmark-consumer-{index}")
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

    preview_first_latencies = [
        metric.first_preview_latency_ms
        for metric in session_metrics_by_context.values()
        if metric.first_preview_latency_ms is not None
    ]
    final_first_latencies = [
        metric.first_final_latency_ms
        for metric in session_metrics_by_context.values()
        if metric.first_final_latency_ms is not None
    ]
    terminal_latencies = [
        metric.terminal_latency_ms
        for metric in session_metrics_by_context.values()
        if metric.terminal_latency_ms is not None
    ]
    preview_emit_count = sum(metric.preview_count for metric in session_metrics_by_context.values())
    final_emit_count = sum(metric.final_count for metric in session_metrics_by_context.values())
    errored_session_count = sum(
        1 for metric in session_metrics_by_context.values() if metric.error_messages
    )

    return ScenarioResult(
        source=source,
        backend_name=source_profile.backend_name,
        shared_instance=source_profile.shared_instance,
        worker_count=worker_count,
        session_count=session_count,
        chunk_ms=chunk_ms,
        chunk_interval_ms=chunk_interval_ms,
        elapsed_seconds=round(elapsed_seconds, 4),
        first_preview_p50_ms=_percentile(preview_first_latencies, 50),
        first_preview_p95_ms=_percentile(preview_first_latencies, 95),
        first_final_p50_ms=_percentile(final_first_latencies, 50),
        first_final_p95_ms=_percentile(final_first_latencies, 95),
        terminal_p50_ms=_percentile(terminal_latencies, 50),
        terminal_p95_ms=_percentile(terminal_latencies, 95),
        preview_emit_count=preview_emit_count,
        final_emit_count=final_emit_count,
        errored_session_count=errored_session_count,
        max_pending_chunk_count=snapshot_stats.max_pending_chunk_count,
        max_busy_stream_count=snapshot_stats.max_busy_stream_count,
        max_draining_stream_count=snapshot_stats.max_draining_stream_count,
        coalesced_chunk_count=snapshot_stats.coalesced_chunk_count,
        busy_worker_count_peak=snapshot_stats.busy_worker_count_peak,
    )


def print_summary(results: list[ScenarioResult]) -> None:
    headers = [
        "workers",
        "sessions",
        "elapsed_s",
        "preview_first_p50",
        "preview_first_p95",
        "final_first_p50",
        "final_first_p95",
        "terminal_p50",
        "terminal_p95",
        "preview_emit",
        "final_emit",
        "max_pending",
        "coalesced",
        "busy_workers",
        "errors",
    ]
    print(" ".join(f"{header:>16}" for header in headers))
    for result in results:
        values = [
            result.worker_count,
            result.session_count,
            f"{result.elapsed_seconds:.2f}",
            _format_metric(result.first_preview_p50_ms),
            _format_metric(result.first_preview_p95_ms),
            _format_metric(result.first_final_p50_ms),
            _format_metric(result.first_final_p95_ms),
            _format_metric(result.terminal_p50_ms),
            _format_metric(result.terminal_p95_ms),
            result.preview_emit_count,
            result.final_emit_count,
            result.max_pending_chunk_count,
            result.coalesced_chunk_count,
            result.busy_worker_count_peak,
            result.errored_session_count,
        ]
        print(" ".join(f"{str(value):>16}" for value in values))


def _format_metric(value: float | None) -> str:
    if value is None:
        return "-"
    return f"{value:.2f}"


async def main_async(args: argparse.Namespace) -> int:
    wav_path = Path(args.wav).resolve()
    wave_audio = read_pcm_wave_file(
        wav_path,
        expected_sample_rate_hz=settings.stt_sample_rate_hz,
        expected_sample_width_bytes=settings.stt_sample_width_bytes,
        expected_channels=settings.stt_channels,
    )
    chunks = split_pcm_bytes(
        wave_audio.raw_bytes,
        sample_rate_hz=wave_audio.sample_rate_hz,
        sample_width_bytes=wave_audio.sample_width_bytes,
        channels=wave_audio.channels,
        chunk_duration_ms=args.chunk_ms,
    )

    if args.warmup:
        await _run_warmup(
            source=args.source,
            chunks=chunks,
            pending_per_stream=args.pending_per_stream,
            max_running_streams=args.max_running_streams,
        )

    results: list[ScenarioResult] = []
    for worker_count in _parse_int_list(args.workers):
        for session_count in _parse_int_list(args.sessions):
            result = await benchmark_scenario(
                source=args.source,
                chunks=chunks,
                worker_count=worker_count,
                session_count=session_count,
                chunk_ms=args.chunk_ms,
                chunk_interval_ms=args.chunk_interval_ms,
                pending_per_stream=args.pending_per_stream,
                max_running_streams=args.max_running_streams,
                sample_interval_ms=args.sample_interval_ms,
            )
            results.append(result)

    print_summary(results)

    if args.output_json:
        output_path = Path(args.output_json).resolve()
        output_path.write_text(
            json.dumps([asdict(result) for result in results], ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    # 벤치 이후 shared service 캐시를 비워서 일반 실행 상태를 오염시키지 않는다.
    dependency_module._get_shared_speech_to_text_service.cache_clear()
    return 0


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    return asyncio.run(main_async(args))


if __name__ == "__main__":
    raise SystemExit(main())
