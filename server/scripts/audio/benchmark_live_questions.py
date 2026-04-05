"""실시간 질문 감지 모델을 오프라인 데이터셋으로 벤치마크한다."""

from __future__ import annotations

import argparse
import json
import statistics
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[3]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


from server.app.core.config import settings
from server.app.services.live_questions.models import (  # noqa: E402
    LiveQuestionItem,
    LiveQuestionOperation,
    LiveQuestionRequest,
    LiveQuestionResult,
    LiveQuestionUtterance,
)
from server.app.services.live_questions.question_llm_client import (  # noqa: E402
    LiveQuestionLLMClient,
)


DEFAULT_DATASET_PATH = (
    PROJECT_ROOT / "tests" / "fixtures" / "support" / "live_questions_benchmark_v1.json"
)


def _normalize_text(value: str | None) -> str:
    if not value:
        return ""
    return "".join(ch for ch in value.lower() if ch.isalnum())


def _compute_ratio(numerator: int, denominator: int) -> float:
    if denominator <= 0:
        return 0.0
    return round(numerator / denominator, 4)


def _compute_f1(precision: float, recall: float) -> float:
    if precision <= 0 or recall <= 0:
        return 0.0
    return round((2 * precision * recall) / (precision + recall), 4)


@dataclass(frozen=True, slots=True)
class BenchmarkExpectedOperation:
    """벤치마크 정답 연산."""

    op: str
    accepted_summaries: tuple[str, ...] = ()
    target_question_id: str | None = None

    @classmethod
    def from_payload(cls, payload: dict[str, object]) -> "BenchmarkExpectedOperation":
        return cls(
            op=str(payload.get("op") or ""),
            accepted_summaries=tuple(
                str(item)
                for item in (payload.get("accepted_summaries") or [])
                if item not in {None, ""}
            ),
            target_question_id=(
                str(payload["target_question_id"])
                if payload.get("target_question_id") not in {None, ""}
                else None
            ),
        )


@dataclass(frozen=True, slots=True)
class BenchmarkCase:
    """질문 벤치마크 단일 케이스."""

    case_id: str
    description: str
    utterances: tuple[LiveQuestionUtterance, ...]
    open_questions: tuple[LiveQuestionItem, ...]
    expected_operations: tuple[BenchmarkExpectedOperation, ...]

    @classmethod
    def from_payload(cls, payload: dict[str, object]) -> "BenchmarkCase":
        return cls(
            case_id=str(payload.get("id") or ""),
            description=str(payload.get("description") or ""),
            utterances=tuple(
                LiveQuestionUtterance.from_payload(item)
                for item in (payload.get("utterances") or [])
                if isinstance(item, dict)
            ),
            open_questions=tuple(
                LiveQuestionItem.from_payload(item)
                for item in (payload.get("open_questions") or [])
                if isinstance(item, dict)
            ),
            expected_operations=tuple(
                BenchmarkExpectedOperation.from_payload(item)
                for item in (payload.get("expected_operations") or [])
                if isinstance(item, dict)
            ),
        )

    def to_request(self) -> LiveQuestionRequest:
        return LiveQuestionRequest(
            session_id=f"benchmark-{self.case_id}",
            window_id=self.case_id,
            utterances=self.utterances,
            open_questions=self.open_questions,
            created_at_ms=0,
        )


@dataclass(frozen=True, slots=True)
class BenchmarkDataset:
    """질문 벤치마크 데이터셋."""

    name: str
    description: str
    cases: tuple[BenchmarkCase, ...]


@dataclass(frozen=True, slots=True)
class CaseEvaluation:
    """단일 케이스 평가 결과."""

    case_id: str
    description: str
    latency_ms: float
    exact_match: bool
    add_true_positive: int
    add_false_positive: int
    add_false_negative: int
    close_true_positive: int
    close_false_positive: int
    close_false_negative: int
    predicted_operations: tuple[LiveQuestionOperation, ...]
    expected_operations: tuple[BenchmarkExpectedOperation, ...]
    error: str | None = None

    def to_payload(self) -> dict[str, object]:
        return {
            "case_id": self.case_id,
            "description": self.description,
            "latency_ms": self.latency_ms,
            "exact_match": self.exact_match,
            "add_true_positive": self.add_true_positive,
            "add_false_positive": self.add_false_positive,
            "add_false_negative": self.add_false_negative,
            "close_true_positive": self.close_true_positive,
            "close_false_positive": self.close_false_positive,
            "close_false_negative": self.close_false_negative,
            "predicted_operations": [item.to_payload() for item in self.predicted_operations],
            "expected_operations": [
                {
                    "op": item.op,
                    "accepted_summaries": list(item.accepted_summaries),
                    "target_question_id": item.target_question_id,
                }
                for item in self.expected_operations
            ],
            "error": self.error,
        }


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="실시간 질문 감지 벤치마크")
    parser.add_argument(
        "--dataset",
        default=str(DEFAULT_DATASET_PATH),
        help="벤치마크 데이터셋 JSON 경로",
    )
    parser.add_argument("--backend", default=settings.live_question_llm_backend)
    parser.add_argument("--model", default=settings.live_question_llm_model)
    parser.add_argument(
        "--base-url",
        default=settings.live_question_llm_base_url or "http://127.0.0.1:11434/v1",
    )
    parser.add_argument("--api-key", default=settings.live_question_llm_api_key or "")
    parser.add_argument(
        "--timeout-seconds",
        type=float,
        default=settings.live_question_llm_timeout_seconds,
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=0,
        help="0이 아니면 앞에서부터 지정 개수만 평가",
    )
    parser.add_argument(
        "--output",
        choices=["text", "json"],
        default="text",
        help="출력 형식",
    )
    parser.add_argument(
        "--save-json",
        default="",
        help="세부 결과를 저장할 JSON 파일 경로",
    )
    return parser


def load_dataset(path: Path, *, limit: int = 0) -> BenchmarkDataset:
    payload = json.loads(path.read_text(encoding="utf-8"))
    cases = [
        BenchmarkCase.from_payload(item)
        for item in (payload.get("cases") or [])
        if isinstance(item, dict)
    ]
    if limit > 0:
        cases = cases[:limit]
    return BenchmarkDataset(
        name=str(payload.get("name") or path.stem),
        description=str(payload.get("description") or ""),
        cases=tuple(cases),
    )


def _match_expected_add(
    predicted: LiveQuestionOperation,
    expected: BenchmarkExpectedOperation,
) -> bool:
    if predicted.op != "add" or expected.op != "add":
        return False
    predicted_summary = _normalize_text(predicted.summary)
    if not predicted_summary:
        return False
    accepted = {_normalize_text(item) for item in expected.accepted_summaries}
    return predicted_summary in accepted


def _match_expected_close(
    predicted: LiveQuestionOperation,
    expected: BenchmarkExpectedOperation,
) -> bool:
    if predicted.op != "close" or expected.op != "close":
        return False
    if not predicted.target_question_id or not expected.target_question_id:
        return False
    return predicted.target_question_id == expected.target_question_id


def evaluate_case(
    *,
    case: BenchmarkCase,
    result: LiveQuestionResult,
    latency_ms: float,
    error: str | None = None,
) -> CaseEvaluation:
    expected = list(case.expected_operations)
    predicted = list(result.operations)
    matched_expected_indexes: set[int] = set()
    matched_predicted_indexes: set[int] = set()

    add_tp = 0
    close_tp = 0

    for expected_index, expected_item in enumerate(expected):
        for predicted_index, predicted_item in enumerate(predicted):
            if predicted_index in matched_predicted_indexes:
                continue
            if expected_item.op == "add" and _match_expected_add(predicted_item, expected_item):
                matched_expected_indexes.add(expected_index)
                matched_predicted_indexes.add(predicted_index)
                add_tp += 1
                break
            if expected_item.op == "close" and _match_expected_close(predicted_item, expected_item):
                matched_expected_indexes.add(expected_index)
                matched_predicted_indexes.add(predicted_index)
                close_tp += 1
                break

    add_fp = sum(
        1
        for index, item in enumerate(predicted)
        if index not in matched_predicted_indexes and item.op == "add"
    )
    close_fp = sum(
        1
        for index, item in enumerate(predicted)
        if index not in matched_predicted_indexes and item.op == "close"
    )
    add_fn = sum(
        1
        for index, item in enumerate(expected)
        if index not in matched_expected_indexes and item.op == "add"
    )
    close_fn = sum(
        1
        for index, item in enumerate(expected)
        if index not in matched_expected_indexes and item.op == "close"
    )

    exact_match = (
        add_fp == 0
        and close_fp == 0
        and add_fn == 0
        and close_fn == 0
        and error is None
    )

    return CaseEvaluation(
        case_id=case.case_id,
        description=case.description,
        latency_ms=round(latency_ms, 1),
        exact_match=exact_match,
        add_true_positive=add_tp,
        add_false_positive=add_fp,
        add_false_negative=add_fn,
        close_true_positive=close_tp,
        close_false_positive=close_fp,
        close_false_negative=close_fn,
        predicted_operations=tuple(predicted),
        expected_operations=tuple(expected),
        error=error,
    )


def _summarize(dataset: BenchmarkDataset, evaluations: list[CaseEvaluation]) -> dict[str, object]:
    add_tp = sum(item.add_true_positive for item in evaluations)
    add_fp = sum(item.add_false_positive for item in evaluations)
    add_fn = sum(item.add_false_negative for item in evaluations)
    close_tp = sum(item.close_true_positive for item in evaluations)
    close_fp = sum(item.close_false_positive for item in evaluations)
    close_fn = sum(item.close_false_negative for item in evaluations)

    add_precision = _compute_ratio(add_tp, add_tp + add_fp)
    add_recall = _compute_ratio(add_tp, add_tp + add_fn)
    close_precision = _compute_ratio(close_tp, close_tp + close_fp)
    close_recall = _compute_ratio(close_tp, close_tp + close_fn)

    latencies = [item.latency_ms for item in evaluations]
    errors = [item for item in evaluations if item.error]
    failures = [item for item in evaluations if not item.exact_match]

    return {
        "dataset": {
            "name": dataset.name,
            "description": dataset.description,
            "case_count": len(dataset.cases),
        },
        "metrics": {
            "exact_match_rate": _compute_ratio(
                sum(1 for item in evaluations if item.exact_match),
                len(evaluations),
            ),
            "add_precision": add_precision,
            "add_recall": add_recall,
            "add_f1": _compute_f1(add_precision, add_recall),
            "close_precision": close_precision,
            "close_recall": close_recall,
            "close_f1": _compute_f1(close_precision, close_recall),
            "average_latency_ms": round(statistics.mean(latencies), 1) if latencies else 0.0,
            "p50_latency_ms": round(statistics.median(latencies), 1) if latencies else 0.0,
            "p90_latency_ms": round(_percentile(latencies, 0.9), 1) if latencies else 0.0,
            "error_count": len(errors),
            "failure_count": len(failures),
        },
        "cases": [item.to_payload() for item in evaluations],
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


def _print_text_summary(
    *,
    dataset: BenchmarkDataset,
    summary: dict[str, object],
    backend: str,
    model: str,
    base_url: str,
) -> None:
    metrics = summary["metrics"]
    print(f"dataset={dataset.name}")
    print(f"description={dataset.description}")
    print(f"backend={backend}")
    print(f"model={model}")
    print(f"base_url={base_url}")
    print(f"case_count={summary['dataset']['case_count']}")
    print(
        "exact_match_rate={0} add_precision={1} add_recall={2} add_f1={3}".format(
            metrics["exact_match_rate"],
            metrics["add_precision"],
            metrics["add_recall"],
            metrics["add_f1"],
        )
    )
    print(
        "close_precision={0} close_recall={1} close_f1={2}".format(
            metrics["close_precision"],
            metrics["close_recall"],
            metrics["close_f1"],
        )
    )
    print(
        "latency_ms avg={0} p50={1} p90={2} errors={3} failures={4}".format(
            metrics["average_latency_ms"],
            metrics["p50_latency_ms"],
            metrics["p90_latency_ms"],
            metrics["error_count"],
            metrics["failure_count"],
        )
    )

    failed_cases = [
        item
        for item in summary["cases"]
        if (not item["exact_match"]) or item.get("error")
    ]
    if not failed_cases:
        print("failed_cases=0")
        return

    print("failed_cases=")
    for item in failed_cases[:10]:
        predicted = ", ".join(
            _format_operation_payload(operation)
            for operation in item.get("predicted_operations") or []
        ) or "<none>"
        expected = ", ".join(
            _format_expected_payload(operation)
            for operation in item.get("expected_operations") or []
        ) or "<none>"
        error = item.get("error")
        print(f"  - case={item['case_id']} latency_ms={item['latency_ms']}")
        print(f"    description={item['description']}")
        print(f"    expected={expected}")
        print(f"    predicted={predicted}")
        if error:
            print(f"    error={error}")


def _format_operation_payload(payload: dict[str, object]) -> str:
    op = str(payload.get("op") or "")
    if op == "add":
        return f"add:{payload.get('summary')}"
    return f"close:{payload.get('target_question_id')}"


def _format_expected_payload(payload: dict[str, object]) -> str:
    op = str(payload.get("op") or "")
    if op == "add":
        accepted = payload.get("accepted_summaries") or []
        first = accepted[0] if accepted else ""
        return f"add:{first}"
    return f"close:{payload.get('target_question_id')}"


def run_benchmark(
    *,
    dataset: BenchmarkDataset,
    backend: str,
    model: str,
    base_url: str,
    api_key: str | None,
    timeout_seconds: float,
) -> list[CaseEvaluation]:
    client = LiveQuestionLLMClient(
        backend_name=backend,
        model=model,
        base_url=base_url,
        api_key=api_key,
        timeout_seconds=timeout_seconds,
    )

    evaluations: list[CaseEvaluation] = []
    for case in dataset.cases:
        request = case.to_request()
        started_at = time.perf_counter()
        error: str | None = None
        try:
            result = client.analyze(request)
        except Exception as exc:  # pragma: no cover - 네트워크/모델 오류
            error = f"{type(exc).__name__}: {exc}"
            result = LiveQuestionResult(
                session_id=request.session_id,
                window_id=request.window_id,
                operations=(),
            )
        latency_ms = (time.perf_counter() - started_at) * 1000
        evaluations.append(
            evaluate_case(
                case=case,
                result=result,
                latency_ms=latency_ms,
                error=error,
            )
        )
    return evaluations


def main() -> int:
    args = _build_parser().parse_args()
    dataset = load_dataset(Path(args.dataset).resolve(), limit=args.limit)
    evaluations = run_benchmark(
        dataset=dataset,
        backend=args.backend,
        model=args.model,
        base_url=args.base_url,
        api_key=args.api_key or None,
        timeout_seconds=args.timeout_seconds,
    )
    summary = _summarize(dataset, evaluations)

    if args.save_json:
        output_path = Path(args.save_json).resolve()
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(
            json.dumps(summary, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    if args.output == "json":
        print(json.dumps(summary, ensure_ascii=False, indent=2))
        return 0

    _print_text_summary(
        dataset=dataset,
        summary=summary,
        backend=args.backend,
        model=args.model,
        base_url=args.base_url,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
