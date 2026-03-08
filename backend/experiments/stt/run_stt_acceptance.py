"""STT acceptance 러너.

샘플 묶음(dataset)과 기준 임계값을 읽어 실제 백엔드가
허용 가능한 정확도/통과율을 유지하는지 검증한다.
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[3]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from backend.app.core.config import settings  # noqa: E402
from backend.experiments.stt.benchmark_stt_backends import benchmark_backend, print_summary  # noqa: E402


@dataclass(frozen=True)
class AcceptanceThreshold:
    """샘플 또는 전체에 적용할 합격 기준."""

    max_wer_kept: float | None = None
    max_cer_kept: float | None = None
    min_guard_keep_rate_vs_raw: float | None = None
    max_rtf_end_to_end: float | None = None


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="STT acceptance 러너")
    parser.add_argument("--dataset", required=True, help="acceptance dataset JSON 경로")
    parser.add_argument("--backend", required=True, help="검증할 STT backend 이름")
    parser.add_argument("--backend-model", help="backend=model_id 형식의 모델 override")
    parser.add_argument("--chunk-ms", type=int, default=250)
    parser.add_argument("--warmup", action="store_true")
    parser.add_argument("--output-json", help="결과 저장 JSON 경로")
    return parser


@lru_cache(maxsize=1)
def _load_acceptance_profiles() -> dict[str, Any]:
    return json.loads(settings.acceptance_profiles_config_path.read_text(encoding="utf-8"))


def _resolve_acceptance_threshold_profile(profile_name: str) -> dict[str, Any]:
    profiles = _load_acceptance_profiles()
    profile = profiles.get(profile_name)
    if profile is None:
        raise ValueError(f"지원하지 않는 acceptance threshold profile입니다: {profile_name}")
    return profile


def load_acceptance_dataset(path: Path) -> tuple[list[dict[str, Any]], AcceptanceThreshold]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    samples = payload["samples"]
    threshold_payload = payload.get("default_threshold", {})
    if "default_threshold_profile" in payload:
        threshold_payload = _resolve_acceptance_threshold_profile(
            payload["default_threshold_profile"]
        )
    default_threshold = AcceptanceThreshold(**threshold_payload)
    return samples, default_threshold


def evaluate_acceptance(
    result: dict[str, Any],
    samples: list[dict[str, Any]],
    default_threshold: AcceptanceThreshold,
) -> dict[str, Any]:
    sample_thresholds = {}
    for sample in samples:
        threshold_payload = sample.get("threshold", {})
        if "threshold_profile" in sample:
            threshold_payload = _resolve_acceptance_threshold_profile(
                sample["threshold_profile"]
            )
        sample_thresholds[sample["name"]] = AcceptanceThreshold(**threshold_payload)
    evaluation_samples: list[dict[str, Any]] = []
    has_failure = False

    for sample_result in result["samples"]:
        threshold = merge_thresholds(default_threshold, sample_thresholds.get(sample_result["sample_name"]))
        failures = evaluate_sample(sample_result, threshold)
        if failures:
            has_failure = True
        evaluation_samples.append(
            {
                "sample_name": sample_result["sample_name"],
                "passed": not failures,
                "failures": failures,
            }
        )

    aggregate_failures = evaluate_aggregate(result["aggregate"], default_threshold)
    if aggregate_failures:
        has_failure = True

    return {
        "backend": result["backend"],
        "model_id": result["model_id"],
        "passed": not has_failure,
        "samples": evaluation_samples,
        "aggregate_failures": aggregate_failures,
    }


def merge_thresholds(
    default_threshold: AcceptanceThreshold,
    override: AcceptanceThreshold | None,
) -> AcceptanceThreshold:
    if override is None:
        return default_threshold
    return AcceptanceThreshold(
        max_wer_kept=override.max_wer_kept if override.max_wer_kept is not None else default_threshold.max_wer_kept,
        max_cer_kept=override.max_cer_kept if override.max_cer_kept is not None else default_threshold.max_cer_kept,
        min_guard_keep_rate_vs_raw=(
            override.min_guard_keep_rate_vs_raw
            if override.min_guard_keep_rate_vs_raw is not None
            else default_threshold.min_guard_keep_rate_vs_raw
        ),
        max_rtf_end_to_end=(
            override.max_rtf_end_to_end
            if override.max_rtf_end_to_end is not None
            else default_threshold.max_rtf_end_to_end
        ),
    )


def evaluate_sample(sample_result: dict[str, Any], threshold: AcceptanceThreshold) -> list[str]:
    failures: list[str] = []
    if threshold.max_wer_kept is not None:
        wer = sample_result.get("wer_kept", {}).get("rate")
        if wer is None or wer > threshold.max_wer_kept:
            failures.append(f"wer_kept>{threshold.max_wer_kept}")
    if threshold.max_cer_kept is not None:
        cer = sample_result.get("cer_kept", {}).get("rate")
        if cer is None or cer > threshold.max_cer_kept:
            failures.append(f"cer_kept>{threshold.max_cer_kept}")
    if threshold.min_guard_keep_rate_vs_raw is not None:
        guard_keep = sample_result.get("guard_keep_rate_vs_raw")
        if guard_keep is None or guard_keep < threshold.min_guard_keep_rate_vs_raw:
            failures.append(f"guard_keep_rate_vs_raw<{threshold.min_guard_keep_rate_vs_raw}")
    if threshold.max_rtf_end_to_end is not None:
        rtf = sample_result.get("rtf_end_to_end")
        if rtf is None or rtf > threshold.max_rtf_end_to_end:
            failures.append(f"rtf_end_to_end>{threshold.max_rtf_end_to_end}")
    return failures


def evaluate_aggregate(aggregate: dict[str, Any], threshold: AcceptanceThreshold) -> list[str]:
    failures: list[str] = []
    if threshold.max_wer_kept is not None and "avg_wer_kept" in aggregate:
        if aggregate["avg_wer_kept"] > threshold.max_wer_kept:
            failures.append(f"avg_wer_kept>{threshold.max_wer_kept}")
    if threshold.max_cer_kept is not None and "avg_cer_kept" in aggregate:
        if aggregate["avg_cer_kept"] > threshold.max_cer_kept:
            failures.append(f"avg_cer_kept>{threshold.max_cer_kept}")
    if threshold.min_guard_keep_rate_vs_raw is not None:
        if aggregate["avg_guard_keep_rate_vs_raw"] < threshold.min_guard_keep_rate_vs_raw:
            failures.append(f"avg_guard_keep_rate_vs_raw<{threshold.min_guard_keep_rate_vs_raw}")
    if threshold.max_rtf_end_to_end is not None:
        if aggregate["avg_rtf_end_to_end"] > threshold.max_rtf_end_to_end:
            failures.append(f"avg_rtf_end_to_end>{threshold.max_rtf_end_to_end}")
    return failures


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()

    dataset_path = Path(args.dataset).resolve()
    samples, default_threshold = load_acceptance_dataset(dataset_path)

    benchmark_payload = argparse.Namespace(
        dataset=str(dataset_path),
        wav=None,
        name="acceptance",
        reference_text=None,
        reference_file=None,
        source="system_audio",
        backends=[args.backend],
        backend_models=[args.backend_model] if args.backend_model else [],
        chunk_ms=args.chunk_ms,
        warmup=args.warmup,
        output_json=None,
    )

    from backend.experiments.stt.benchmark_stt_backends import (
        _BENCHMARK_CONFIG,
        _parse_backend_model_overrides,
        load_samples,
    )

    _BENCHMARK_CONFIG["backend_model_overrides"] = _parse_backend_model_overrides(
        benchmark_payload.backend_models or []
    )
    benchmark_samples = load_samples(benchmark_payload)
    result = benchmark_backend(args.backend, benchmark_samples, args.chunk_ms, args.warmup)
    print_summary([result])

    evaluation = evaluate_acceptance(result, samples, default_threshold)
    payload = {"result": result, "evaluation": evaluation}

    if args.output_json:
        output_path = Path(args.output_json).resolve()
        output_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"saved_json={output_path}")
    else:
        print(json.dumps(payload, ensure_ascii=False, indent=2))

    if not evaluation["passed"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
