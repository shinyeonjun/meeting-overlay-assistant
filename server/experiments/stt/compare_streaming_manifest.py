"""STT 실험에서 compare streaming manifest 검증 흐름을 수행한다."""
from __future__ import annotations

import argparse
import json
import statistics
import subprocess
import sys
import tempfile
import wave
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[3]
BENCHMARK_SCRIPT = PROJECT_ROOT / "server" / "experiments" / "stt" / "benchmark_realtime_stt.py"


@dataclass(frozen=True)
class ManifestSample:
    """비교 대상 오디오 샘플."""

    name: str
    audio_path: Path
    audio_format: str
    reference_text: str


def build_parser() -> argparse.ArgumentParser:
    """공통 흐름에서 build parser 로직을 수행한다."""
    parser = argparse.ArgumentParser(description="manifest 기준으로 실시간 STT 후보를 비교합니다.")
    parser.add_argument("--manifest", required=True, help="JSONL manifest 경로")
    parser.add_argument("--limit", type=int, default=5, help="비교할 샘플 수")
    parser.add_argument("--source", choices=["mic", "system_audio", "file"], default="system_audio")
    parser.add_argument("--chunk-ms", type=int, default=120)
    parser.add_argument("--warmup", action="store_true")
    parser.add_argument("--sherpa-model-path", required=True)
    parser.add_argument("--sensevoice-model-path", default="")
    parser.add_argument("--python-exe", default=str((PROJECT_ROOT / "venv" / "Scripts" / "python.exe").resolve()))
    parser.add_argument(
        "--output-dir",
        default="",
        help="결과를 저장할 디렉터리. 비우면 temp 디렉터리를 사용합니다.",
    )
    return parser


def load_samples(manifest_path: Path, limit: int) -> list[ManifestSample]:
    """공통 흐름에서 load samples 로직을 수행한다."""
    samples: list[ManifestSample] = []
    with manifest_path.open("r", encoding="utf-8-sig") as handle:
        for line in handle:
            if not line.strip():
                continue
            payload = json.loads(line)
            audio_path = Path(payload["audio_path"]).resolve()
            samples.append(
                ManifestSample(
                    name=audio_path.stem,
                    audio_path=audio_path,
                    audio_format=str(payload.get("audio_format", audio_path.suffix.lstrip("."))).lower(),
                    reference_text=str(payload.get("reference_display") or payload.get("reference_raw") or "").strip(),
                )
            )
            if len(samples) >= limit:
                break
    if not samples:
        raise ValueError("manifest에서 비교할 샘플을 찾지 못했습니다.")
    return samples


def ensure_wav(sample: ManifestSample, wav_dir: Path) -> Path:
    """공통 흐름에서 ensure wav 로직을 수행한다."""
    if sample.audio_path.suffix.lower() == ".wav":
        return sample.audio_path

    if sample.audio_format != "pcm":
        raise ValueError(f"지원하지 않는 오디오 형식입니다: {sample.audio_format}")

    wav_path = wav_dir / f"{sample.name}.wav"
    raw_bytes = sample.audio_path.read_bytes()
    with wave.open(str(wav_path), "wb") as wav_file:
        wav_file.setnchannels(1)
        wav_file.setsampwidth(2)
        wav_file.setframerate(16000)
        wav_file.writeframes(raw_bytes)
    return wav_path


def run_benchmark(
    *,
    sample: ManifestSample,
    wav_path: Path,
    args: argparse.Namespace,
    sample_output_path: Path,
) -> dict[str, Any]:
    """공통 흐름에서 run benchmark 로직을 수행한다."""
    command = [
        args.python_exe,
        str(BENCHMARK_SCRIPT),
        "--wav",
        str(wav_path),
        "--name",
        sample.name,
        "--source",
        args.source,
        "--chunk-ms",
        str(args.chunk_ms),
        "--backend",
        "faster_whisper_streaming",
        "--backend",
        "sherpa_onnx_streaming",
        "--backend-model",
        f"sherpa_onnx_streaming={Path(args.sherpa_model_path).resolve()}",
        "--backend-python",
        f"sherpa_onnx_streaming={Path(args.python_exe).resolve()}",
        "--reference-text",
        sample.reference_text,
        "--output-json",
        str(sample_output_path),
    ]

    if args.sensevoice_model_path:
        sensevoice_model_path = str(Path(args.sensevoice_model_path).resolve())
        python_path = str(Path(args.python_exe).resolve())
        command.extend(
            [
                "--backend",
                "sensevoice_small_streaming@cpu",
                "--backend-model",
                f"sensevoice_small_streaming@cpu={sensevoice_model_path}",
                "--backend-python",
                f"sensevoice_small_streaming@cpu={python_path}",
                "--backend-arg",
                "sensevoice_small_streaming@cpu=--device",
                "--backend-arg",
                "sensevoice_small_streaming@cpu=cpu",
                "--backend",
                "sensevoice_small_streaming@cuda",
                "--backend-model",
                f"sensevoice_small_streaming@cuda={sensevoice_model_path}",
                "--backend-python",
                f"sensevoice_small_streaming@cuda={python_path}",
                "--backend-arg",
                "sensevoice_small_streaming@cuda=--device",
                "--backend-arg",
                "sensevoice_small_streaming@cuda=cuda:0",
            ]
        )

    if args.warmup:
        command.append("--warmup")

    completed = subprocess.run(
        command,
        cwd=str(PROJECT_ROOT),
        check=False,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    if completed.returncode != 0 and not sample_output_path.exists():
        raise RuntimeError(
            "실시간 비교 실행 실패: "
            f"sample={sample.name} returncode={completed.returncode} "
            f"stdout={completed.stdout.strip()} stderr={completed.stderr.strip()}"
        )
    payload = json.loads(sample_output_path.read_text(encoding="utf-8"))
    return {
        "sample": sample.name,
        "wav_path": str(wav_path),
        "results": payload["results"],
        "stdout": completed.stdout,
    }


def aggregate(sample_results: list[dict[str, Any]]) -> dict[str, Any]:
    """공통 흐름에서 aggregate 로직을 수행한다."""
    by_backend: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for sample_result in sample_results:
        for result in sample_result["results"]:
            by_backend[str(result["backend"])].append(result)

    summary: dict[str, Any] = {}
    for backend, rows in by_backend.items():
        success_rows = [row for row in rows if not row.get("error")]
        error_rows = [row for row in rows if row.get("error")]
        summary[backend] = {
            "samples": len(rows),
            "successes": len(success_rows),
            "errors": len(error_rows),
            "avg_first_partial_latency_seconds": _avg(success_rows, "first_partial_latency_seconds"),
            "avg_first_final_latency_seconds": _avg(success_rows, "first_final_latency_seconds"),
            "avg_rtf_total": _avg(success_rows, "rtf_total"),
            "avg_partial_count": _avg(success_rows, "partial_count"),
            "avg_final_count": _avg(success_rows, "final_count"),
            "avg_wer_final": _avg_nested(success_rows, "wer_final", "rate"),
            "avg_cer_final": _avg_nested(success_rows, "cer_final", "rate"),
        }
    return summary


def _avg(rows: list[dict[str, Any]], key: str) -> float | None:
    values = [float(value) for row in rows if (value := row.get(key)) is not None]
    if not values:
        return None
    return round(statistics.mean(values), 4)


def _avg_nested(rows: list[dict[str, Any]], key: str, nested_key: str) -> float | None:
    values = [
        float(nested_value)
        for row in rows
        if isinstance(row.get(key), dict) and (nested_value := row[key].get(nested_key)) is not None
    ]
    if not values:
        return None
    return round(statistics.mean(values), 4)


def print_summary(summary: dict[str, Any]) -> None:
    """공통 흐름에서 print summary 로직을 수행한다."""
    print("")
    print("실시간 비교 요약")
    for backend, payload in summary.items():
        print(
            f"- {backend}: "
            f"success={payload['successes']}/{payload['samples']} "
            f"partial={payload['avg_first_partial_latency_seconds']} "
            f"final={payload['avg_first_final_latency_seconds']} "
            f"rtf={payload['avg_rtf_total']} "
            f"wer={payload['avg_wer_final']} "
            f"cer={payload['avg_cer_final']}"
        )


def main() -> None:
    """공통 흐름에서 main 로직을 수행한다."""
    args = build_parser().parse_args()
    manifest_path = Path(args.manifest).resolve()
    samples = load_samples(manifest_path, args.limit)

    if args.output_dir:
        output_dir = Path(args.output_dir).resolve()
        output_dir.mkdir(parents=True, exist_ok=True)
        temp_context = None
    else:
        temp_context = tempfile.TemporaryDirectory(prefix="caps-live-stt-compare-")
        output_dir = Path(temp_context.name)

    wav_dir = output_dir / "wav"
    wav_dir.mkdir(parents=True, exist_ok=True)

    sample_results: list[dict[str, Any]] = []
    try:
        for index, sample in enumerate(samples, start=1):
            wav_path = ensure_wav(sample, wav_dir)
            sample_output_path = output_dir / f"{sample.name}.json"
            sample_result = run_benchmark(
                sample=sample,
                wav_path=wav_path,
                args=args,
                sample_output_path=sample_output_path,
            )
            sample_results.append(sample_result)
            print(f"[{index}/{len(samples)}] {sample.name} 완료")

        summary = aggregate(sample_results)
        payload = {
            "manifest": str(manifest_path),
            "limit": args.limit,
            "source": args.source,
            "chunk_ms": args.chunk_ms,
            "samples": sample_results,
            "summary": summary,
        }
        summary_path = output_dir / "summary.json"
        summary_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        print_summary(summary)
        print(f"saved_json={summary_path}")
    finally:
        if temp_context is not None:
            temp_context.cleanup()


if __name__ == "__main__":
    main()
