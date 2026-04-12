"""STT 실험에서 benchmark stt backends 검증 흐름을 수행한다."""
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

from server.app.api.http import dependencies as dependency_module  # noqa: E402
from server.app.core.config import settings  # noqa: E402
from server.app.services.audio.stt.benchmarking import (  # noqa: E402
    GuardPassStats,
    compute_character_error_rate,
    compute_word_error_rate,
)
from server.app.services.audio.stt.speech_to_text_factory import create_speech_to_text_service  # noqa: E402
from server.app.services.audio.io.wav_chunk_reader import (  # noqa: E402
    read_pcm_wave_file,
    split_pcm_bytes,
)


@dataclass(frozen=True)
class BenchmarkSample:
    """벤치마크에 사용할 샘플."""

    name: str
    wav_path: Path
    source: str
    reference_text: str | None = None


def build_parser() -> argparse.ArgumentParser:
    """공통 흐름에서 build parser 로직을 수행한다."""
    parser = argparse.ArgumentParser(description="STT 백엔드 벤치마크를 실행합니다.")
    parser.add_argument("--dataset", help="샘플 목록 JSON 파일 경로")
    parser.add_argument("--wav", help="단일 WAV 파일 경로")
    parser.add_argument("--name", default="single-sample", help="단일 샘플 이름")
    parser.add_argument("--reference-text", help="단일 샘플 기준 정답 텍스트")
    parser.add_argument("--reference-file", help="단일 샘플 기준 정답 텍스트 파일 경로")
    parser.add_argument("--source", default="system_audio", choices=["mic", "system_audio", "file"])
    parser.add_argument(
        "--backend",
        action="append",
        dest="backends",
        help="비교할 STT 백엔드. 여러 번 지정 가능",
    )
    parser.add_argument(
        "--backend-model",
        action="append",
        dest="backend_models",
        help="백엔드별 모델 지정. 형식: backend=model_id",
    )
    parser.add_argument("--chunk-ms", type=int, default=250, help="입력 chunk 길이(ms)")
    parser.add_argument("--warmup", action="store_true", help="첫 샘플 이전에 간단한 warmup 수행")
    parser.add_argument("--output-json", help="벤치마크 결과를 저장할 JSON 파일 경로")
    return parser


def load_samples(args: argparse.Namespace) -> list[BenchmarkSample]:
    """공통 흐름에서 load samples 로직을 수행한다."""
    if args.dataset:
        dataset_path = Path(args.dataset).resolve()
        data = json.loads(dataset_path.read_text(encoding="utf-8"))
        return [
            BenchmarkSample(
                name=item["name"],
                wav_path=(dataset_path.parent / item["wav_path"]).resolve(),
                source=item.get("source", args.source),
                reference_text=_resolve_reference_text(
                    inline_text=item.get("reference_text"),
                    reference_file=item.get("reference_file"),
                    base_dir=dataset_path.parent,
                ),
            )
            for item in data
        ]

    if not args.wav:
        raise ValueError("--dataset 또는 --wav 중 하나는 반드시 지정해야 합니다.")

    return [
        BenchmarkSample(
            name=args.name,
            wav_path=Path(args.wav).resolve(),
            source=args.source,
            reference_text=_resolve_reference_text(
                inline_text=args.reference_text,
                reference_file=args.reference_file,
                base_dir=Path.cwd(),
            ),
        )
    ]


def benchmark_backend(backend_name: str, samples: list[BenchmarkSample], chunk_ms: int, warmup: bool) -> dict:
    """공통 흐름에서 benchmark backend 로직을 수행한다."""
    backend_model_id = _resolve_backend_model_id(backend_name, benchmark_config())
    service = create_speech_to_text_service(
        backend_name=backend_name,
        model_id=backend_model_id,
        model_path=settings.stt_model_path,
        base_model_id=settings.stt_base_model_id,
        installation_path=settings.ryzen_ai_installation_path,
        encoder_model_path=settings.stt_encoder_model_path,
        decoder_model_path=settings.stt_decoder_model_path,
        encoder_rai_path=settings.stt_encoder_rai_path,
        base_url=settings.stt_base_url,
        api_key=settings.stt_api_key,
        timeout_seconds=settings.stt_timeout_seconds,
        language=settings.stt_language,
        device=settings.stt_device,
        compute_type=settings.stt_compute_type,
        cpu_threads=settings.stt_cpu_threads,
        beam_size=settings.stt_beam_size,
        sample_rate_hz=settings.stt_sample_rate_hz,
        sample_width_bytes=settings.stt_sample_width_bytes,
        channels=settings.stt_channels,
        silence_rms_threshold=settings.stt_silence_rms_threshold,
    )

    if warmup and samples:
        _run_warmup(service, samples[0], chunk_ms)

    sample_results = [benchmark_sample(service, backend_name, sample, chunk_ms) for sample in samples]
    return {
        "backend": backend_name,
        "model_id": backend_model_id,
        "samples": sample_results,
        "aggregate": _aggregate_sample_results(sample_results),
    }


def benchmark_sample(service, backend_name: str, sample: BenchmarkSample, chunk_ms: int) -> dict:
    """공통 흐름에서 benchmark sample 로직을 수행한다."""
    wave_audio = read_pcm_wave_file(
        sample.wav_path,
        expected_sample_rate_hz=settings.stt_sample_rate_hz,
        expected_sample_width_bytes=settings.stt_sample_width_bytes,
        expected_channels=settings.stt_channels,
    )
    audio_duration_seconds = len(wave_audio.raw_bytes) / (
        wave_audio.sample_rate_hz * wave_audio.sample_width_bytes * wave_audio.channels
    )
    chunks = split_pcm_bytes(
        wave_audio.raw_bytes,
        sample_rate_hz=wave_audio.sample_rate_hz,
        sample_width_bytes=wave_audio.sample_width_bytes,
        channels=wave_audio.channels,
        chunk_duration_ms=chunk_ms,
    )
    chunks.append(b"\x00" * settings.stt_sample_rate_hz * settings.stt_sample_width_bytes)

    segmenter = dependency_module._build_audio_segmenter(sample.source)
    guard = dependency_module._build_transcription_guard(sample.source)
    rss_sampler = _create_rss_sampler()
    baseline_rss = rss_sampler()
    peak_rss = baseline_rss

    raw_texts: list[str] = []
    kept_texts: list[str] = []
    raw_segment_count = 0
    non_empty_segment_count = 0
    kept_segment_count = 0
    transcribe_seconds = 0.0
    first_text_latency_seconds: float | None = None
    first_guarded_latency_seconds: float | None = None

    benchmark_start = time.perf_counter()

    for chunk in chunks:
        segments = segmenter.split(chunk)
        for segment in segments:
            raw_segment_count += 1
            started_at = time.perf_counter()
            result = service.transcribe(segment)
            elapsed = time.perf_counter() - started_at
            transcribe_seconds += elapsed
            peak_rss = max(peak_rss, rss_sampler())

            normalized_text = result.text.strip()
            if normalized_text:
                non_empty_segment_count += 1
                raw_texts.append(normalized_text)
                first_text_latency_seconds = first_text_latency_seconds or (
                    time.perf_counter() - benchmark_start
                )

            if guard.should_keep(result):
                kept_segment_count += 1
                kept_texts.append(normalized_text)
                first_guarded_latency_seconds = first_guarded_latency_seconds or (
                    time.perf_counter() - benchmark_start
                )

    total_elapsed_seconds = time.perf_counter() - benchmark_start
    raw_transcript = " ".join(raw_texts).strip()
    kept_transcript = " ".join(kept_texts).strip()
    guard_stats = GuardPassStats(
        raw_segment_count=raw_segment_count,
        non_empty_segment_count=non_empty_segment_count,
        kept_segment_count=kept_segment_count,
    )

    result = {
        "backend": backend_name,
        "sample_name": sample.name,
        "source": sample.source,
        "wav_path": str(sample.wav_path),
        "audio_duration_seconds": round(audio_duration_seconds, 4),
        "chunk_ms": chunk_ms,
        "raw_segment_count": raw_segment_count,
        "non_empty_segment_count": non_empty_segment_count,
        "kept_segment_count": kept_segment_count,
        "guard_non_empty_rate": round(guard_stats.non_empty_rate, 4),
        "guard_keep_rate_vs_raw": round(guard_stats.keep_rate_vs_raw, 4),
        "guard_keep_rate_vs_non_empty": round(guard_stats.keep_rate_vs_non_empty, 4),
        "transcribe_seconds": round(transcribe_seconds, 4),
        "total_elapsed_seconds": round(total_elapsed_seconds, 4),
        "rtf_transcribe_only": round(transcribe_seconds / audio_duration_seconds, 4),
        "rtf_end_to_end": round(total_elapsed_seconds / audio_duration_seconds, 4),
        "first_text_latency_seconds": _round_or_none(first_text_latency_seconds),
        "first_guarded_latency_seconds": _round_or_none(first_guarded_latency_seconds),
        "memory_rss_baseline_bytes": baseline_rss,
        "memory_rss_peak_bytes": peak_rss,
        "memory_rss_delta_bytes": max(peak_rss - baseline_rss, 0),
        "raw_transcript": raw_transcript,
        "kept_transcript": kept_transcript,
    }

    if sample.reference_text:
        result["reference_text"] = sample.reference_text
        result["wer_raw"] = compute_word_error_rate(sample.reference_text, raw_transcript).__dict__
        result["cer_raw"] = compute_character_error_rate(sample.reference_text, raw_transcript).__dict__
        result["wer_kept"] = compute_word_error_rate(sample.reference_text, kept_transcript).__dict__
        result["cer_kept"] = compute_character_error_rate(sample.reference_text, kept_transcript).__dict__

    return result


def _aggregate_sample_results(sample_results: list[dict]) -> dict:
    rtf_end_to_end = [item["rtf_end_to_end"] for item in sample_results]
    rtf_transcribe_only = [item["rtf_transcribe_only"] for item in sample_results]
    keep_rates = [item["guard_keep_rate_vs_raw"] for item in sample_results]
    first_text_latencies = [
        item["first_text_latency_seconds"]
        for item in sample_results
        if item["first_text_latency_seconds"] is not None
    ]
    first_guarded_latencies = [
        item["first_guarded_latency_seconds"]
        for item in sample_results
        if item["first_guarded_latency_seconds"] is not None
    ]

    aggregate = {
        "sample_count": len(sample_results),
        "avg_rtf_end_to_end": round(statistics.mean(rtf_end_to_end), 4) if rtf_end_to_end else 0.0,
        "avg_rtf_transcribe_only": round(statistics.mean(rtf_transcribe_only), 4)
        if rtf_transcribe_only
        else 0.0,
        "avg_guard_keep_rate_vs_raw": round(statistics.mean(keep_rates), 4) if keep_rates else 0.0,
        "avg_first_text_latency_seconds": _round_or_none(
            statistics.mean(first_text_latencies) if first_text_latencies else None
        ),
        "avg_first_guarded_latency_seconds": _round_or_none(
            statistics.mean(first_guarded_latencies) if first_guarded_latencies else None
        ),
        "max_memory_rss_peak_bytes": max(
            (item["memory_rss_peak_bytes"] for item in sample_results),
            default=0,
        ),
    }

    if any("wer_kept" in item for item in sample_results):
        kept_wer = [item["wer_kept"]["rate"] for item in sample_results if "wer_kept" in item]
        kept_cer = [item["cer_kept"]["rate"] for item in sample_results if "cer_kept" in item]
        aggregate["avg_wer_kept"] = round(statistics.mean(kept_wer), 4) if kept_wer else 0.0
        aggregate["avg_cer_kept"] = round(statistics.mean(kept_cer), 4) if kept_cer else 0.0

    return aggregate


def _run_warmup(service, sample: BenchmarkSample, chunk_ms: int) -> None:
    wave_audio = read_pcm_wave_file(
        sample.wav_path,
        expected_sample_rate_hz=settings.stt_sample_rate_hz,
        expected_sample_width_bytes=settings.stt_sample_width_bytes,
        expected_channels=settings.stt_channels,
    )
    chunks = split_pcm_bytes(
        wave_audio.raw_bytes,
        sample_rate_hz=wave_audio.sample_rate_hz,
        sample_width_bytes=wave_audio.sample_width_bytes,
        channels=wave_audio.channels,
        chunk_duration_ms=chunk_ms,
    )
    if not chunks:
        return

    segmenter = dependency_module._build_audio_segmenter(sample.source)
    for segment in segmenter.split(chunks[0]):
        service.transcribe(segment)
        break


def _resolve_reference_text(
    inline_text: str | None,
    reference_file: str | None,
    base_dir: Path,
) -> str | None:
    if reference_file:
        reference_path = Path(reference_file)
        if not reference_path.is_absolute():
            reference_path = (base_dir / reference_path).resolve()
        return _read_text_file(reference_path)
    return inline_text


def _read_text_file(path: Path) -> str:
    for encoding in ("utf-8-sig", "utf-8", "cp949"):
        try:
            return path.read_text(encoding=encoding).strip()
        except UnicodeDecodeError:
            continue
    raise RuntimeError(f"기준 텍스트 파일을 읽을 수 없습니다: {path}")


def _create_rss_sampler():
    try:
        import psutil
    except ImportError:
        return lambda: 0

    process = psutil.Process()
    return lambda: process.memory_info().rss


def _round_or_none(value: float | None) -> float | None:
    if value is None:
        return None
    return round(value, 4)


def print_summary(results: list[dict]) -> None:
    """공통 흐름에서 print summary 로직을 수행한다."""
    for result in results:
        aggregate = result["aggregate"]
        print(
            f"[{result['backend']}] model={result['model_id']} "
            f"avg_rtf={aggregate['avg_rtf_end_to_end']}, "
            f"avg_guard_keep={aggregate['avg_guard_keep_rate_vs_raw']}, "
            f"avg_first_guarded_latency={aggregate['avg_first_guarded_latency_seconds']}"
        )
        if "avg_wer_kept" in aggregate:
            print(
                f"  - avg_wer_kept={aggregate['avg_wer_kept']}, "
                f"avg_cer_kept={aggregate['avg_cer_kept']}"
            )


def main() -> None:
    """공통 흐름에서 main 로직을 수행한다."""
    parser = build_parser()
    args = parser.parse_args()

    samples = load_samples(args)
    backends = args.backends or [settings.stt_backend]
    _BENCHMARK_CONFIG["backend_model_overrides"] = _parse_backend_model_overrides(
        args.backend_models or []
    )
    results = [
        benchmark_backend(
            backend_name=backend_name,
            samples=samples,
            chunk_ms=args.chunk_ms,
            warmup=args.warmup,
        )
        for backend_name in backends
    ]

    print_summary(results)
    payload = {"results": results}
    if args.output_json:
        output_path = Path(args.output_json).resolve()
        output_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"saved_json={output_path}")
    else:
        print(json.dumps(payload, ensure_ascii=False, indent=2))


_BENCHMARK_CONFIG: dict[str, Any] = {"backend_model_overrides": {}}


def benchmark_config() -> dict[str, Any]:
    """공통 흐름에서 benchmark config 로직을 수행한다."""
    return _BENCHMARK_CONFIG


def _parse_backend_model_overrides(items: list[str]) -> dict[str, str]:
    overrides: dict[str, str] = {}
    for item in items:
        if "=" not in item:
            raise ValueError("--backend-model 형식은 backend=model_id 여야 합니다.")
        backend_name, model_id = item.split("=", 1)
        backend_name = backend_name.strip()
        model_id = model_id.strip()
        if not backend_name or not model_id:
            raise ValueError("--backend-model 형식은 backend=model_id 여야 합니다.")
        overrides[backend_name] = model_id
    return overrides


def _resolve_backend_model_id(backend_name: str, config: dict[str, Any]) -> str:
    overrides = config["backend_model_overrides"]
    if backend_name in overrides:
        return overrides[backend_name]
    if backend_name == "faster_whisper" and settings.stt_model_id.startswith("amd/"):
        return "deepdml/faster-whisper-large-v3-turbo-ct2"
    return settings.stt_model_id


if __name__ == "__main__":
    main()


