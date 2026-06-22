"""Assistant RAG chat benchmark runner.

This script calls AssistantChatService.generate_answer() directly so benchmark
runs do not create assistant conversations, messages, or response jobs.
"""

from __future__ import annotations

import argparse
import json
import statistics
import sys
import time
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[3]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from server.app.api.http.dependency_providers.reporting import get_assistant_chat_service  # noqa: E402
from server.app.api.http.wiring.persistence import (  # noqa: E402
    get_postgresql_database,
    initialize_primary_persistence,
)
from server.app.core.ai_service_profiles import resolve_completion_client_profile  # noqa: E402
from server.app.core.config import settings  # noqa: E402
from server.app.core.workspace_defaults import DEFAULT_WORKSPACE_ID  # noqa: E402


DEFAULT_QUERIES = (
    "가장 최근 회의는 뭐였지?",
    "6월 회의는 있었어?",
    "5월 회의는 몇 개인데?",
    "이 회의에서 결정사항이나 다음 할 일이 있었어?",
    "회의에서 채널 이름이나 삐쭈TV 관련 이야기가 있었어?",
)

READ_ONLY_TABLES = (
    "assistant_conversations",
    "assistant_messages",
    "assistant_response_jobs",
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Assistant RAG chat benchmark")
    parser.add_argument("--query", action="append", dest="queries", help="Question to benchmark")
    parser.add_argument("--queries-file", help="UTF-8 JSON or text file containing questions")
    parser.add_argument("--workspace-id", default=DEFAULT_WORKSPACE_ID)
    parser.add_argument("--session-id", default="")
    parser.add_argument("--source-type", action="append", dest="source_types")
    parser.add_argument("--limit", type=int, default=6)
    parser.add_argument("--timeout-seconds", type=float, default=0.0)
    parser.add_argument("--output", choices=["text", "json"], default="text")
    parser.add_argument("--save-json", default="")
    return parser


def load_queries(args: argparse.Namespace) -> list[str]:
    queries: list[str] = []
    if args.queries_file:
        path = Path(args.queries_file).resolve()
        if path.suffix.lower() == ".json":
            payload = json.loads(path.read_text(encoding="utf-8"))
            if isinstance(payload, list):
                queries.extend(str(item) for item in payload)
            elif isinstance(payload, dict):
                queries.extend(str(item) for item in payload.get("queries") or [])
        else:
            queries.extend(
                line.strip()
                for line in path.read_text(encoding="utf-8").splitlines()
                if line.strip()
            )
    queries.extend(args.queries or [])
    if not queries:
        queries.extend(DEFAULT_QUERIES)
    return [query.strip() for query in queries if query and query.strip()]


def query_read_only_counts() -> dict[str, int]:
    database = get_postgresql_database()
    counts: dict[str, int] = {}
    with database.transaction() as connection:
        for table_name in READ_ONLY_TABLES:
            row = connection.execute(f"SELECT COUNT(*) AS count FROM {table_name}").fetchone()
            counts[table_name] = int(row["count"] if row else 0)
    return counts


def summarize_sources(sources) -> dict[str, Any]:
    by_type: dict[str, int] = {}
    for source in sources:
        by_type[source.source_type] = by_type.get(source.source_type, 0) + 1
    return {
        "count": len(sources),
        "by_type": by_type,
        "items": [
            {
                "rank": index + 1,
                "source_type": source.source_type,
                "document_title": source.document_title,
                "chunk_heading": source.chunk_heading,
                "distance": source.distance,
                "rank_score": source.rank_score,
                "session_id": source.session_id,
                "source_ref": source.source_ref,
                "text_preview": " ".join(source.chunk_text.split())[:180],
            }
            for index, source in enumerate(sources[:5])
        ],
    }


def run_benchmark(
    *,
    queries: list[str],
    workspace_id: str,
    source_types: tuple[str, ...],
    session_id: str | None,
    limit: int,
    timeout_seconds: float,
) -> dict[str, Any]:
    initialize_primary_persistence()
    before_counts = query_read_only_counts()
    service = get_assistant_chat_service()
    if service is None:
        raise RuntimeError("assistant chat service is unavailable")

    cases: list[dict[str, Any]] = []
    for index, query in enumerate(queries, start=1):
        started_at = time.perf_counter()
        status = "completed"
        error = None
        try:
            result = service.generate_answer(
                workspace_id=workspace_id,
                query=query,
                source_types=source_types,
                session_id=session_id,
                limit=limit,
            )
        except Exception as exc:  # pragma: no cover - benchmark safety net
            status = "failed"
            error = f"{type(exc).__name__}: {exc}"
            result = None
        elapsed_seconds = round(time.perf_counter() - started_at, 3)
        if timeout_seconds > 0 and elapsed_seconds > timeout_seconds and status == "completed":
            status = "slow"
        cases.append(
            {
                "index": index,
                "query": query,
                "status": status,
                "elapsed_seconds": elapsed_seconds,
                "error": error,
                "answer": result.answer if result else "",
                "answer_chars": len(result.answer) if result else 0,
                "sources": summarize_sources(result.sources if result else []),
            }
        )

    after_counts = query_read_only_counts()
    latencies = [case["elapsed_seconds"] for case in cases]
    completed = [case for case in cases if case["status"] in {"completed", "slow"}]
    profile = resolve_completion_client_profile(
        "assistant_default",
        settings,
        fallback_model=settings.llm_model,
        fallback_base_url=settings.llm_base_url or "http://127.0.0.1:11434/v1",
        fallback_api_key=settings.llm_api_key,
        fallback_timeout_seconds=settings.llm_timeout_seconds,
    )
    return {
        "benchmark": "assistant_chat",
        "workspace_id": workspace_id,
        "source_types": list(source_types),
        "session_id": session_id,
        "limit": limit,
        "config": {
            "completion_backend": profile.backend_name,
            "completion_model": profile.model,
            "completion_base_url": profile.base_url,
            "retrieval_embedding_backend": settings.retrieval_embedding_backend,
            "retrieval_embedding_model": settings.retrieval_embedding_model,
        },
        "read_only_check": {
            "before": before_counts,
            "after": after_counts,
            "unchanged": before_counts == after_counts,
        },
        "metrics": {
            "case_count": len(cases),
            "completed_count": len(completed),
            "failed_count": sum(1 for case in cases if case["status"] == "failed"),
            "slow_count": sum(1 for case in cases if case["status"] == "slow"),
            "average_latency_seconds": round(statistics.mean(latencies), 3) if latencies else 0,
            "p50_latency_seconds": round(statistics.median(latencies), 3) if latencies else 0,
            "p90_latency_seconds": round(_percentile(latencies, 0.9), 3) if latencies else 0,
            "average_source_count": round(
                statistics.mean(case["sources"]["count"] for case in cases), 2
            )
            if cases
            else 0,
        },
        "cases": cases,
    }


def _percentile(values: list[float], quantile: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    if len(ordered) == 1:
        return ordered[0]
    index = (len(ordered) - 1) * quantile
    lower = int(index)
    upper = min(lower + 1, len(ordered) - 1)
    weight = index - lower
    return ordered[lower] * (1 - weight) + ordered[upper] * weight


def print_text_summary(payload: dict[str, Any]) -> None:
    metrics = payload["metrics"]
    print("benchmark=assistant_chat")
    print(f"model={payload['config']['completion_model']}")
    print(
        "cases={0} completed={1} failed={2} slow={3}".format(
            metrics["case_count"],
            metrics["completed_count"],
            metrics["failed_count"],
            metrics["slow_count"],
        )
    )
    print(
        "latency_seconds avg={0} p50={1} p90={2} avg_sources={3}".format(
            metrics["average_latency_seconds"],
            metrics["p50_latency_seconds"],
            metrics["p90_latency_seconds"],
            metrics["average_source_count"],
        )
    )
    print(f"read_only_unchanged={payload['read_only_check']['unchanged']}")
    for case in payload["cases"]:
        print(
            "  - #{0} status={1} elapsed={2}s sources={3}: {4}".format(
                case["index"],
                case["status"],
                case["elapsed_seconds"],
                case["sources"]["count"],
                case["query"],
            )
        )
        if case["error"]:
            print(f"    error={case['error']}")


def main() -> int:
    args = build_parser().parse_args()
    payload = run_benchmark(
        queries=load_queries(args),
        workspace_id=args.workspace_id,
        source_types=tuple(args.source_types or ()),
        session_id=args.session_id or None,
        limit=args.limit,
        timeout_seconds=args.timeout_seconds,
    )
    if args.save_json:
        output_path = Path(args.save_json).resolve()
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
    if args.output == "json":
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    else:
        print_text_summary(payload)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
