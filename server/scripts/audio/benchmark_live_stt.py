"""split live STT 지연/품질 벤치마크 스크립트."""

from __future__ import annotations

import argparse
import asyncio
import json
import math
import os
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from urllib import request

import psycopg
import websockets
from websockets.exceptions import ConnectionClosed, ConnectionClosedError, ConnectionClosedOK

PROJECT_ROOT = Path(__file__).resolve().parents[3]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from server.app.core.config import settings
from server.app.services.audio.io.wav_chunk_reader import read_pcm_wave_file, split_pcm_bytes


@dataclass
class WebSocketMetrics:
    """WebSocket 수신 기준 체감 지표."""

    payload_count: int = 0
    preview_count: int = 0
    live_final_count: int = 0
    archive_final_count: int = 0
    late_archive_final_count: int = 0
    first_preview_ms: float | None = None
    first_live_final_ms: float | None = None
    first_archive_final_ms: float | None = None
    first_late_archive_final_ms: float | None = None
    start_epoch_ms: int | None = None
    connect_ms: float | None = None


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="split live STT 지연 벤치마크를 실행합니다.")
    parser.add_argument("--wav", required=True, help="16kHz/mono/16-bit PCM WAV 파일 경로")
    parser.add_argument("--title", default="STT 벤치마크", help="생성할 세션 제목")
    parser.add_argument("--source", default="system_audio", choices=["mic", "system_audio", "mic_and_audio"])
    parser.add_argument("--control-base-url", default="http://127.0.0.1:8011")
    parser.add_argument("--live-base-url", default="http://127.0.0.1:8012")
    parser.add_argument("--chunk-ms", type=int, default=250, help="전송 chunk 크기(ms)")
    parser.add_argument(
        "--delay-ms",
        type=int,
        default=250,
        help="chunk 전송 간격(ms). 실측은 chunk-ms와 동일하게 두는 것이 권장됩니다.",
    )
    parser.add_argument("--append-silence-ms", type=int, default=2500, help="후행 무음 길이(ms)")
    parser.add_argument("--post-stream-wait-ms", type=int, default=4000, help="전송 종료 후 수신 대기(ms)")
    parser.add_argument("--settle-timeout-ms", type=int, default=20000, help="DB 안정화 대기 최대(ms)")
    parser.add_argument("--settle-poll-ms", type=int, default=1000, help="DB 안정화 polling 주기(ms)")
    parser.add_argument("--stable-rounds", type=int, default=3, help="연속 동일 상태 확인 횟수")
    parser.add_argument("--max-audio-ms", type=int, default=0, help="0이면 전체 WAV 사용")
    parser.add_argument("--output", choices=["text", "json"], default="text")
    return parser


def _create_session(*, control_base_url: str, title: str, source: str) -> str:
    payload = json.dumps(
        {
            "title": title,
            "mode": "meeting",
            "source": source,
        }
    ).encode("utf-8")
    req = request.Request(
        url=f"{control_base_url.rstrip('/')}/api/v1/sessions/",
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with request.urlopen(req, timeout=20) as response:
        body = json.loads(response.read().decode("utf-8"))
    return body["id"]


def _start_session(*, control_base_url: str, session_id: str) -> None:
    req = request.Request(
        url=f"{control_base_url.rstrip('/')}/api/v1/sessions/{session_id}/start",
        data=b"",
        method="POST",
    )
    with request.urlopen(req, timeout=20) as response:
        response.read()


def _clip_audio(raw_bytes: bytes, *, bytes_per_ms: int, max_audio_ms: int) -> bytes:
    if max_audio_ms <= 0:
        return raw_bytes
    max_bytes = bytes_per_ms * max_audio_ms
    return raw_bytes[:max_bytes]


def _build_silence_chunks(*, sample_rate_hz: int, sample_width_bytes: int, channels: int, chunk_ms: int, total_ms: int) -> list[bytes]:
    if total_ms <= 0:
        return []
    bytes_per_ms = int(sample_rate_hz * sample_width_bytes * channels / 1000)
    silence = b"\x00" * (bytes_per_ms * total_ms)
    return split_pcm_bytes(
        silence,
        sample_rate_hz=sample_rate_hz,
        sample_width_bytes=sample_width_bytes,
        channels=channels,
        chunk_duration_ms=chunk_ms,
    )


def _build_ws_url(*, live_base_url: str, session_id: str, source: str) -> str:
    ws_url = live_base_url.rstrip("/").replace("http://", "ws://").replace("https://", "wss://")
    return f"{ws_url}/api/v1/ws/audio/{session_id}?input_source={source}"


def _elapsed_ms(start_perf: float) -> float:
    return round((time.perf_counter() - start_perf) * 1000, 1)


async def _receive_payloads(
    websocket,
    metrics: WebSocketMetrics,
    *,
    start_perf: float,
) -> None:
    try:
        while True:
            raw_payload = await websocket.recv()
            payload = json.loads(raw_payload)
            if payload.get("error"):
                raise RuntimeError(f"live websocket error: {payload['error']}")
            utterances = payload.get("utterances") or []
            if not utterances:
                continue
            metrics.payload_count += 1
            now_ms = _elapsed_ms(start_perf)
            for utterance in utterances:
                kind = utterance.get("kind", "archive_final")
                if kind in {"preview", "partial"}:
                    metrics.preview_count += 1
                    if metrics.first_preview_ms is None:
                        metrics.first_preview_ms = now_ms
                elif kind == "live_final":
                    metrics.live_final_count += 1
                    if metrics.first_live_final_ms is None:
                        metrics.first_live_final_ms = now_ms
                elif kind == "late_archive_final":
                    metrics.late_archive_final_count += 1
                    if metrics.first_late_archive_final_ms is None:
                        metrics.first_late_archive_final_ms = now_ms
                else:
                    metrics.archive_final_count += 1
                    if metrics.first_archive_final_ms is None:
                        metrics.first_archive_final_ms = now_ms
    except (ConnectionClosedOK, ConnectionClosedError, ConnectionClosed):
        return


async def _send_chunks(
    websocket,
    *,
    chunks: list[bytes],
    delay_ms: int,
    post_stream_wait_ms: int,
) -> None:
    for chunk in chunks:
        await websocket.send(chunk)
        await asyncio.sleep(delay_ms / 1000)
    await asyncio.sleep(post_stream_wait_ms / 1000)
    await websocket.close()


async def _stream_and_measure(
    *,
    live_base_url: str,
    session_id: str,
    source: str,
    chunks: list[bytes],
    delay_ms: int,
    post_stream_wait_ms: int,
) -> WebSocketMetrics:
    metrics = WebSocketMetrics()
    ws_url = _build_ws_url(live_base_url=live_base_url, session_id=session_id, source=source)
    connect_start_perf = time.perf_counter()
    async with websockets.connect(ws_url, max_size=None) as websocket:
        metrics.connect_ms = round((time.perf_counter() - connect_start_perf) * 1000, 1)
        start_perf = time.perf_counter()
        metrics.start_epoch_ms = int(time.time() * 1000)
        sender = asyncio.create_task(
            _send_chunks(
                websocket,
                chunks=chunks,
                delay_ms=delay_ms,
                post_stream_wait_ms=post_stream_wait_ms,
            )
        )
        receiver = asyncio.create_task(
            _receive_payloads(
                websocket,
                metrics,
                start_perf=start_perf,
            )
        )
        await asyncio.gather(sender, receiver, return_exceptions=True)
    return metrics


def _query_session_signature(connection, session_id: str) -> tuple[int, int | None]:
    with connection.cursor() as cursor:
        cursor.execute(
            """
            SELECT COUNT(*) AS n, MAX(seq_num) AS max_seq
            FROM utterances
            WHERE session_id = %s
            """,
            (session_id,),
        )
        row = cursor.fetchone()
    if row is None:
        return 0, None
    return int(row[0]), (int(row[1]) if row[1] is not None else None)


def _wait_for_db_settle(
    *,
    dsn: str,
    session_id: str,
    settle_timeout_ms: int,
    settle_poll_ms: int,
    stable_rounds: int,
) -> None:
    deadline = time.perf_counter() + (settle_timeout_ms / 1000)
    last_signature: tuple[int, int | None] | None = None
    stable_count = 0
    with psycopg.connect(dsn) as connection:
        while time.perf_counter() < deadline:
            signature = _query_session_signature(connection, session_id)
            if signature == last_signature:
                stable_count += 1
                if stable_count >= stable_rounds:
                    return
            else:
                stable_count = 0
                last_signature = signature
            time.sleep(settle_poll_ms / 1000)


def _query_db_metrics(*, dsn: str, session_id: str) -> dict[str, Any]:
    with psycopg.connect(dsn) as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT
                    COUNT(*) AS utterance_count,
                    ROUND(AVG(latency_ms)::numeric, 1) AS average_latency_ms,
                    percentile_cont(0.5) within group (order by latency_ms) AS p50_latency_ms,
                    percentile_cont(0.9) within group (order by latency_ms) AS p90_latency_ms,
                    percentile_cont(0.95) within group (order by latency_ms) AS p95_latency_ms,
                    MAX(latency_ms) AS max_latency_ms,
                    ROUND(AVG(confidence)::numeric, 3) AS average_confidence,
                    percentile_cont(0.5) within group (order by confidence) AS p50_confidence,
                    SUM(CASE WHEN latency_ms > 2000 THEN 1 ELSE 0 END) AS gt_2000_count,
                    SUM(CASE WHEN latency_ms > 3500 THEN 1 ELSE 0 END) AS gt_3500_count,
                    SUM(CASE WHEN latency_ms > 5000 THEN 1 ELSE 0 END) AS gt_5000_count,
                    MIN(stt_backend) AS stt_backend
                FROM utterances
                WHERE session_id = %s
                """,
                (session_id,),
            )
            row = cursor.fetchone()
            cursor.execute(
                """
                SELECT seq_num, latency_ms, confidence, text
                FROM utterances
                WHERE session_id = %s
                ORDER BY seq_num ASC
                LIMIT 5
                """,
                (session_id,),
            )
            sample_rows = cursor.fetchall()
    if row is None:
        return {
            "utterance_count": 0,
            "samples": [],
        }

    utterance_count = int(row[0] or 0)
    return {
        "utterance_count": utterance_count,
        "average_latency_ms": float(row[1]) if row[1] is not None else None,
        "p50_latency_ms": float(row[2]) if row[2] is not None else None,
        "p90_latency_ms": float(row[3]) if row[3] is not None else None,
        "p95_latency_ms": float(row[4]) if row[4] is not None else None,
        "max_latency_ms": int(row[5]) if row[5] is not None else None,
        "average_confidence": float(row[6]) if row[6] is not None else None,
        "p50_confidence": float(row[7]) if row[7] is not None else None,
        "gt_2000_count": int(row[8] or 0),
        "gt_3500_count": int(row[9] or 0),
        "gt_5000_count": int(row[10] or 0),
        "stt_backend": row[11],
        "samples": [
            {
                "seq_num": int(sample[0]),
                "latency_ms": int(sample[1]) if sample[1] is not None else None,
                "confidence": float(sample[2]) if sample[2] is not None else None,
                "text": sample[3],
            }
            for sample in sample_rows
        ],
    }


def _query_runtime_monitor(*, live_base_url: str, session_id: str) -> dict[str, Any]:
    monitor_url = (
        f"{live_base_url.rstrip('/')}/api/v1/runtime/monitor?session_id={session_id}"
    )
    with request.urlopen(monitor_url, timeout=20) as response:
        payload = json.loads(response.read().decode("utf-8"))
    return payload.get("audio_pipeline") or {}


def _to_relative_ms(*, absolute_epoch_ms: int | None, start_epoch_ms: int | None) -> float | None:
    if absolute_epoch_ms is None or start_epoch_ms is None:
        return None
    return round(max(absolute_epoch_ms - start_epoch_ms, 0), 1)


def _resolve_preview_timing_ms(
    *,
    runtime_monitor: dict[str, Any],
    relative_key: str,
    absolute_key: str,
    start_epoch_ms: int | None,
) -> float | None:
    relative_ms = runtime_monitor.get(relative_key)
    if isinstance(relative_ms, (int, float)):
        return round(float(relative_ms), 1)
    return _to_relative_ms(
        absolute_epoch_ms=runtime_monitor.get(absolute_key),
        start_epoch_ms=start_epoch_ms,
    )


def _print_text_summary(summary: dict[str, Any]) -> None:
    print(f"session_id={summary['session_id']}")
    print(f"source={summary['source']}")
    print(f"audio_seconds={summary['audio_seconds']}")
    print(f"chunk_ms={summary['chunk_ms']} delay_ms={summary['delay_ms']}")
    print(f"connect_ms={summary['ws']['connect_ms']}")
    print(
        "ws_first_preview_ms={0} ws_first_live_final_ms={1} ws_first_archive_final_ms={2} ws_first_late_archive_final_ms={3}".format(
            summary["ws"]["first_preview_ms"],
            summary["ws"]["first_live_final_ms"],
            summary["ws"]["first_archive_final_ms"],
            summary["ws"]["first_late_archive_final_ms"],
        )
    )
    print(
        "db_latency_ms avg={0} p50={1} p90={2} p95={3} max={4}".format(
            summary["db"]["average_latency_ms"],
            summary["db"]["p50_latency_ms"],
            summary["db"]["p90_latency_ms"],
            summary["db"]["p95_latency_ms"],
            summary["db"]["max_latency_ms"],
        )
    )
    print(
        "db_confidence avg={0} p50={1} utterances={2} gt_2000={3} gt_3500={4} gt_5000={5}".format(
            summary["db"]["average_confidence"],
            summary["db"]["p50_confidence"],
            summary["db"]["utterance_count"],
            summary["db"]["gt_2000_count"],
            summary["db"]["gt_3500_count"],
            summary["db"]["gt_5000_count"],
        )
    )
    live_compare = summary.get("live_compare") or {}
    if live_compare:
        print(
            "live_vs_archive compare={0} exact={1} changed={2} change_ratio={3} avg_similarity={4} avg_delay_ms={5}".format(
                live_compare.get("compare_count"),
                live_compare.get("exact_match_count"),
                live_compare.get("changed_count"),
                live_compare.get("change_ratio"),
                live_compare.get("average_similarity"),
                live_compare.get("average_delay_ms"),
            )
        )
    preview_diagnostics = summary.get("preview_diagnostics") or {}
    if preview_diagnostics:
        print(
            "preview_diag candidates={0} preview_candidates={1} live_final_candidates={2} emitted={3} emitted_preview={4} emitted_live_final={5} guard_rejected={6} length_rejected={7} backpressure={8}".format(
                preview_diagnostics.get("candidate_count"),
                preview_diagnostics.get("candidate_preview_count"),
                preview_diagnostics.get("candidate_live_final_count"),
                preview_diagnostics.get("emitted_count"),
                preview_diagnostics.get("emitted_preview_count"),
                preview_diagnostics.get("emitted_live_final_count"),
                preview_diagnostics.get("guard_rejected_count"),
                preview_diagnostics.get("length_rejected_count"),
                preview_diagnostics.get("backpressure_count"),
            )
        )
        print(
            "preview_cycles first_attempted_anchor_ms={0} first_productive_anchor_ms={1} productive_gap_ms={2} empty_before_productive={3}".format(
                preview_diagnostics.get("first_attempted_anchor_ms"),
                preview_diagnostics.get("first_productive_anchor_ms"),
                preview_diagnostics.get("first_productive_gap_ms"),
                preview_diagnostics.get("empty_cycles_before_first_candidate_count"),
            )
        )
        print(
            "preview_timing first_anchor_ms={0} ready_offset_ms={1} picked_offset_ms={2} job_started_offset_ms={3} sherpa_non_empty_offset_ms={4} candidate_offset_ms={5}".format(
                preview_diagnostics.get("first_anchor_ms"),
                preview_diagnostics.get("first_ready_ms"),
                preview_diagnostics.get("first_picked_ms"),
                preview_diagnostics.get("first_job_started_ms"),
                preview_diagnostics.get("first_sherpa_non_empty_ms"),
                preview_diagnostics.get("first_candidate_ms"),
            )
        )
        print(
            "preview_scheduler ready_pending_finals={0} ready_busy_workers={1} picked_pending_finals={2} picked_busy_workers={3}".format(
                preview_diagnostics.get("first_ready_pending_final_chunk_count"),
                preview_diagnostics.get("first_ready_busy_worker_count"),
                preview_diagnostics.get("first_picked_pending_final_chunk_count"),
                preview_diagnostics.get("first_picked_busy_worker_count"),
            )
        )
        print(
            "preview_skip busy={0} preferred_final={1} first_busy_skip_ms={2} first_preferred_final_skip_ms={3}".format(
                preview_diagnostics.get("notify_skipped_busy_count"),
                preview_diagnostics.get("notify_skipped_preferred_final_count"),
                preview_diagnostics.get("first_busy_skip_ms"),
                preview_diagnostics.get("first_preferred_final_skip_ms"),
            )
        )
        print(
            "preview_skip_state busy_pending_finals={0} busy_has_preview={1} busy_workers={2} busy_job_kind={3} preferred_final_pending_finals={4} preferred_final_has_preview={5} preferred_final_busy_workers={6} preferred_final_busy_job_kind={7}".format(
                preview_diagnostics.get("first_busy_skip_pending_final_chunk_count"),
                preview_diagnostics.get("first_busy_skip_has_pending_preview_chunk"),
                preview_diagnostics.get("first_busy_skip_busy_worker_count"),
                preview_diagnostics.get("first_busy_skip_busy_job_kind"),
                preview_diagnostics.get("first_preferred_final_skip_pending_final_chunk_count"),
                preview_diagnostics.get("first_preferred_final_skip_has_pending_preview_chunk"),
                preview_diagnostics.get("first_preferred_final_skip_busy_worker_count"),
                preview_diagnostics.get("first_preferred_final_skip_busy_job_kind"),
            )
        )
    if summary["db"].get("samples"):
        print("samples=")
        for sample in summary["db"]["samples"]:
            print(
                f"  - seq={sample['seq_num']} latency_ms={sample['latency_ms']} confidence={sample['confidence']}: {sample['text']}"
            )


async def main() -> None:
    parser = _build_parser()
    args = parser.parse_args()

    wave_audio = read_pcm_wave_file(
        Path(args.wav),
        expected_sample_rate_hz=16000,
        expected_sample_width_bytes=2,
        expected_channels=1,
    )
    bytes_per_ms = int(
        wave_audio.sample_rate_hz * wave_audio.sample_width_bytes * wave_audio.channels / 1000
    )
    clipped_audio = _clip_audio(
        wave_audio.raw_bytes,
        bytes_per_ms=bytes_per_ms,
        max_audio_ms=args.max_audio_ms,
    )
    audio_duration_ms = round(len(clipped_audio) / bytes_per_ms, 1) if bytes_per_ms > 0 else 0.0
    audio_chunks = split_pcm_bytes(
        clipped_audio,
        sample_rate_hz=wave_audio.sample_rate_hz,
        sample_width_bytes=wave_audio.sample_width_bytes,
        channels=wave_audio.channels,
        chunk_duration_ms=args.chunk_ms,
    )
    silence_chunks = _build_silence_chunks(
        sample_rate_hz=wave_audio.sample_rate_hz,
        sample_width_bytes=wave_audio.sample_width_bytes,
        channels=wave_audio.channels,
        chunk_ms=args.chunk_ms,
        total_ms=args.append_silence_ms,
    )
    session_id = _create_session(
        control_base_url=args.control_base_url,
        title=args.title,
        source=args.source,
    )
    _start_session(control_base_url=args.control_base_url, session_id=session_id)
    ws_metrics = await _stream_and_measure(
        live_base_url=args.live_base_url,
        session_id=session_id,
        source=args.source,
        chunks=[*audio_chunks, *silence_chunks],
        delay_ms=args.delay_ms,
        post_stream_wait_ms=args.post_stream_wait_ms,
    )

    dsn = settings.postgresql_dsn or os.getenv("POSTGRESQL_DSN")
    if not dsn:
        raise RuntimeError("POSTGRESQL_DSN이 설정되어 있지 않습니다.")
    _wait_for_db_settle(
        dsn=dsn,
        session_id=session_id,
        settle_timeout_ms=args.settle_timeout_ms,
        settle_poll_ms=args.settle_poll_ms,
        stable_rounds=args.stable_rounds,
    )
    db_metrics = _query_db_metrics(dsn=dsn, session_id=session_id)
    runtime_monitor = _query_runtime_monitor(
        live_base_url=args.live_base_url,
        session_id=session_id,
    )
    summary = {
        "session_id": session_id,
        "source": args.source,
        "audio_seconds": round(audio_duration_ms / 1000, 2),
        "chunk_ms": args.chunk_ms,
        "delay_ms": args.delay_ms,
        "control_base_url": args.control_base_url,
        "live_base_url": args.live_base_url,
        "ws": {
            "payload_count": ws_metrics.payload_count,
            "preview_count": ws_metrics.preview_count,
            "live_final_count": ws_metrics.live_final_count,
            "archive_final_count": ws_metrics.archive_final_count,
            "late_archive_final_count": ws_metrics.late_archive_final_count,
            "connect_ms": ws_metrics.connect_ms,
            "first_preview_ms": ws_metrics.first_preview_ms,
            "first_live_final_ms": ws_metrics.first_live_final_ms,
            "first_archive_final_ms": ws_metrics.first_archive_final_ms,
            "first_late_archive_final_ms": ws_metrics.first_late_archive_final_ms,
        },
        "db": db_metrics,
        "live_compare": {
            "compare_count": runtime_monitor.get("live_final_compare_count", 0),
            "exact_match_count": runtime_monitor.get("live_final_exact_match_count", 0),
            "changed_count": runtime_monitor.get("live_final_changed_count", 0),
            "change_ratio": runtime_monitor.get("live_final_change_ratio", 0),
            "average_similarity": runtime_monitor.get("live_final_average_similarity"),
            "average_delay_ms": runtime_monitor.get("live_final_average_delay_ms"),
        },
        "preview_diagnostics": {
            "candidate_count": runtime_monitor.get("preview_candidate_count", 0),
            "candidate_preview_count": runtime_monitor.get("preview_candidate_preview_count", 0),
            "candidate_live_final_count": runtime_monitor.get("preview_candidate_live_final_count", 0),
            "first_attempted_anchor_ms": _to_relative_ms(
                absolute_epoch_ms=runtime_monitor.get("preview_first_attempted_anchor_at_ms"),
                start_epoch_ms=ws_metrics.start_epoch_ms,
            ),
            "first_anchor_ms": _to_relative_ms(
                absolute_epoch_ms=runtime_monitor.get("preview_timeline_anchor_at_ms"),
                start_epoch_ms=ws_metrics.start_epoch_ms,
            ),
            "first_productive_anchor_ms": _to_relative_ms(
                absolute_epoch_ms=runtime_monitor.get("preview_timeline_anchor_at_ms"),
                start_epoch_ms=ws_metrics.start_epoch_ms,
            ),
            "first_productive_gap_ms": runtime_monitor.get("preview_first_productive_gap_ms"),
            "empty_cycles_before_first_candidate_count": runtime_monitor.get(
                "preview_empty_cycles_before_first_candidate_count",
                0,
            ),
            "first_ready_ms": _resolve_preview_timing_ms(
                runtime_monitor=runtime_monitor,
                relative_key="preview_first_ready_relative_ms",
                absolute_key="preview_first_ready_at_ms",
                start_epoch_ms=ws_metrics.start_epoch_ms,
            ),
            "first_job_started_ms": _resolve_preview_timing_ms(
                runtime_monitor=runtime_monitor,
                relative_key="preview_first_job_started_relative_ms",
                absolute_key="preview_first_job_started_at_ms",
                start_epoch_ms=ws_metrics.start_epoch_ms,
            ),
            "first_picked_ms": _resolve_preview_timing_ms(
                runtime_monitor=runtime_monitor,
                relative_key="preview_first_picked_relative_ms",
                absolute_key="preview_first_picked_at_ms",
                start_epoch_ms=ws_metrics.start_epoch_ms,
            ),
            "first_sherpa_non_empty_ms": _resolve_preview_timing_ms(
                runtime_monitor=runtime_monitor,
                relative_key="preview_first_sherpa_non_empty_relative_ms",
                absolute_key="preview_first_sherpa_non_empty_at_ms",
                start_epoch_ms=ws_metrics.start_epoch_ms,
            ),
            "first_candidate_ms": _resolve_preview_timing_ms(
                runtime_monitor=runtime_monitor,
                relative_key="preview_first_candidate_relative_ms",
                absolute_key="preview_first_candidate_at_ms",
                start_epoch_ms=ws_metrics.start_epoch_ms,
            ),
            "first_ready_pending_final_chunk_count": runtime_monitor.get(
                "preview_first_ready_pending_final_chunk_count"
            ),
            "first_ready_busy_worker_count": runtime_monitor.get(
                "preview_first_ready_busy_worker_count"
            ),
            "first_picked_pending_final_chunk_count": runtime_monitor.get(
                "preview_first_picked_pending_final_chunk_count"
            ),
            "first_picked_busy_worker_count": runtime_monitor.get(
                "preview_first_picked_busy_worker_count"
            ),
            "notify_skipped_busy_count": runtime_monitor.get(
                "preview_notify_skipped_busy_count",
                0,
            ),
            "notify_skipped_preferred_final_count": runtime_monitor.get(
                "preview_notify_skipped_preferred_final_count",
                0,
            ),
            "first_busy_skip_ms": _resolve_preview_timing_ms(
                runtime_monitor=runtime_monitor,
                relative_key="preview_first_busy_skip_relative_ms",
                absolute_key="preview_first_busy_skip_at_ms",
                start_epoch_ms=ws_metrics.start_epoch_ms,
            ),
            "first_preferred_final_skip_ms": _resolve_preview_timing_ms(
                runtime_monitor=runtime_monitor,
                relative_key="preview_first_preferred_final_skip_relative_ms",
                absolute_key="preview_first_preferred_final_skip_at_ms",
                start_epoch_ms=ws_metrics.start_epoch_ms,
            ),
            "first_busy_skip_pending_final_chunk_count": runtime_monitor.get(
                "preview_first_busy_skip_pending_final_chunk_count"
            ),
            "first_busy_skip_has_pending_preview_chunk": runtime_monitor.get(
                "preview_first_busy_skip_has_pending_preview_chunk"
            ),
            "first_busy_skip_busy_worker_count": runtime_monitor.get(
                "preview_first_busy_skip_busy_worker_count"
            ),
            "first_busy_skip_busy_job_kind": runtime_monitor.get(
                "preview_first_busy_skip_busy_job_kind"
            ),
            "first_preferred_final_skip_pending_final_chunk_count": runtime_monitor.get(
                "preview_first_preferred_final_skip_pending_final_chunk_count"
            ),
            "first_preferred_final_skip_has_pending_preview_chunk": runtime_monitor.get(
                "preview_first_preferred_final_skip_has_pending_preview_chunk"
            ),
            "first_preferred_final_skip_busy_worker_count": runtime_monitor.get(
                "preview_first_preferred_final_skip_busy_worker_count"
            ),
            "first_preferred_final_skip_busy_job_kind": runtime_monitor.get(
                "preview_first_preferred_final_skip_busy_job_kind"
            ),
            "emitted_count": runtime_monitor.get("preview_emitted_count", 0),
            "emitted_preview_count": runtime_monitor.get("preview_emitted_preview_count", 0),
            "emitted_live_final_count": runtime_monitor.get("preview_emitted_live_final_count", 0),
            "guard_rejected_count": runtime_monitor.get("preview_guard_rejected_count", 0),
            "length_rejected_count": runtime_monitor.get("preview_length_rejected_count", 0),
            "backpressure_count": runtime_monitor.get("preview_backpressure_count", 0),
        },
    }
    if args.output == "json":
        print(json.dumps(summary, ensure_ascii=False, indent=2))
        return
    _print_text_summary(summary)


if __name__ == "__main__":
    asyncio.run(main())
