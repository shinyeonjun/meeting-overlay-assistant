"""실시간 STT 경로의 partial/final latency를 비교하는 벤치마크 스크립트."""

from __future__ import annotations

import argparse
import json
import os
import statistics
import subprocess
import sys
import tempfile
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[3]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from backend.app.core.audio_source_policy import resolve_audio_source_policy  # noqa: E402
from backend.app.core.config import settings  # noqa: E402
from backend.app.services.audio.stt.benchmarking import (  # noqa: E402
    compute_character_error_rate,
    compute_word_error_rate,
)
from backend.app.services.audio.segmentation.speech_segmenter import (  # noqa: E402
    SpeechSegmenter,
    VadSegmenterConfig,
    VadSpeechSegmenter,
)
from backend.app.services.audio.stt.speech_to_text_factory import create_speech_to_text_service  # noqa: E402
from backend.app.services.audio.stt.transcription import StreamingSpeechToTextService  # noqa: E402
from backend.app.services.audio.io.wav_chunk_reader import (  # noqa: E402
    read_pcm_wave_file,
    split_pcm_bytes,
)


@dataclass(frozen=True)
class RealtimeBenchmarkSample:
    """실시간 STT 벤치마크 입력 샘플."""

    name: str
    wav_path: Path
    source: str
    reference_text: str | None = None


@dataclass(frozen=True)
class RealtimeWrapperProfile:
    """외부 실시간 래퍼 벤치마크 프로파일."""

    script_path: Path
    output_format: str
    default_model_id: str
    language: str
    language_arg: str
    base_args: tuple[str, ...]
    model_arg: str


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="실시간 STT partial/final latency를 측정합니다.")
    parser.add_argument("--wav", required=True, help="입력 WAV 파일 경로")
    parser.add_argument("--name", default="single-sample", help="샘플 이름")
    parser.add_argument("--source", default="system_audio", choices=["mic", "system_audio", "file"])
    parser.add_argument("--reference-text", help="정답 텍스트")
    parser.add_argument("--reference-file", help="정답 텍스트 파일")
    parser.add_argument("--backend", action="append", dest="backends", help="비교할 backend를 여러 번 지정합니다.")
    parser.add_argument(
        "--backend-model",
        action="append",
        dest="backend_models",
        help="backend=model_id 형식의 모델 override",
    )
    parser.add_argument(
        "--backend-python",
        action="append",
        dest="backend_pythons",
        help="backend=python.exe 형식의 별도 venv Python 경로",
    )
    parser.add_argument(
        "--backend-arg",
        action="append",
        dest="backend_args",
        help="backend=추가인자 형식의 wrapper backend 추가 인자",
    )
    parser.add_argument("--chunk-ms", type=int, default=120, help="실시간 입력 chunk 길이(ms)")
    parser.add_argument("--warmup", action="store_true", help="첫 샘플로 warmup 실행")
    parser.add_argument("--output-json", help="결과 JSON 저장 경로")
    return parser


def load_sample(args: argparse.Namespace) -> RealtimeBenchmarkSample:
    return RealtimeBenchmarkSample(
        name=args.name,
        wav_path=Path(args.wav).resolve(),
        source=args.source,
        reference_text=_resolve_reference_text(
            inline_text=args.reference_text,
            reference_file=args.reference_file,
        ),
    )


def benchmark_backend(
    backend_name: str,
    sample: RealtimeBenchmarkSample,
    chunk_ms: int,
    warmup: bool,
    backend_model_overrides: dict[str, str],
) -> dict:
    backend_model_id = _resolve_backend_model_id(backend_name, backend_model_overrides)
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

    if warmup:
        _run_warmup(service, sample, chunk_ms)

    return _benchmark_sample(
        service=service,
        backend_name=backend_name,
        model_id=backend_model_id,
        sample=sample,
        chunk_ms=chunk_ms,
    )


def benchmark_wrapper_backend(
    backend_name: str,
    sample: RealtimeBenchmarkSample,
    backend_model_overrides: dict[str, str],
    backend_python_overrides: dict[str, str],
    backend_arg_overrides: dict[str, list[str]],
    wrapper_profiles: dict[str, RealtimeWrapperProfile],
) -> dict:
    profile_backend_name, _ = _split_backend_instance_name(backend_name)
    profile = wrapper_profiles[profile_backend_name]
    backend_model_id = _resolve_wrapper_model_id(backend_name, backend_model_overrides, profile_backend_name, profile)
    python_exe = _resolve_override_value(
        backend_name,
        profile_backend_name,
        backend_python_overrides,
        str(Path(sys.executable).resolve()),
    )
    extra_args = _resolve_backend_args(backend_name, profile_backend_name, backend_arg_overrides)

    command = [
        python_exe,
        str(profile.script_path),
        str(sample.wav_path),
        profile.language_arg,
        profile.language,
        *profile.base_args,
        *extra_args,
        profile.model_arg,
        backend_model_id,
    ]

    started_at = time.perf_counter()
    env = _build_wrapper_subprocess_env()
    completed = subprocess.run(
        command,
        cwd=str(PROJECT_ROOT),
        check=False,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        env=env,
    )
    total_elapsed_seconds = time.perf_counter() - started_at
    if completed.returncode != 0:
        raise RuntimeError(
            "wrapper benchmark failed: "
            f"backend={backend_name} returncode={completed.returncode} "
            f"stdout={completed.stdout.strip()} stderr={completed.stderr.strip()}"
        )

    parsed = _parse_wrapper_output(profile.output_format, completed.stdout)
    wave_audio = read_pcm_wave_file(
        sample.wav_path,
        expected_sample_rate_hz=settings.stt_sample_rate_hz,
        expected_sample_width_bytes=settings.stt_sample_width_bytes,
        expected_channels=settings.stt_channels,
    )
    audio_duration_seconds = len(wave_audio.raw_bytes) / (
        wave_audio.sample_rate_hz * wave_audio.sample_width_bytes * wave_audio.channels
    )
    result = {
        "backend": backend_name,
        "model_id": backend_model_id,
        "sample_name": sample.name,
        "wav_path": str(sample.wav_path),
        "source": sample.source,
        "audio_duration_seconds": round(audio_duration_seconds, 4),
        "chunk_ms": None,
        "partial_count": parsed["partial_count"],
        "final_count": parsed["final_count"],
        "first_partial_latency_seconds": _round_or_none(parsed["first_partial_latency_seconds"]),
        "first_final_latency_seconds": _round_or_none(parsed["first_final_latency_seconds"]),
        "avg_partial_emit_interval_seconds": _round_or_none(_average_intervals(parsed["partial_emit_times"])),
        "avg_final_emit_interval_seconds": _round_or_none(_average_intervals(parsed["final_emit_times"])),
        "partial_cpu_seconds": None,
        "final_cpu_seconds": None,
        "total_elapsed_seconds": round(total_elapsed_seconds, 4),
        "rtf_total": round(total_elapsed_seconds / audio_duration_seconds, 4),
        "rtf_partial_cpu": None,
        "rtf_final_cpu": None,
        "last_partial_transcript": parsed["last_partial_transcript"],
        "final_transcript": parsed["final_transcript"],
    }
    if sample.reference_text:
        result["reference_text"] = sample.reference_text
        result["wer_final"] = compute_word_error_rate(sample.reference_text, parsed["final_transcript"]).__dict__
        result["cer_final"] = compute_character_error_rate(sample.reference_text, parsed["final_transcript"]).__dict__
    return result


def _benchmark_sample(service, backend_name: str, model_id: str, sample: RealtimeBenchmarkSample, chunk_ms: int) -> dict:
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

    source_policy = resolve_audio_source_policy(sample.source, settings)
    segmenter = _build_audio_segmenter(source_policy)

    benchmark_start = time.perf_counter()
    partial_texts: list[str] = []
    final_texts: list[str] = []
    partial_emit_times: list[float] = []
    final_emit_times: list[float] = []
    partial_count = 0
    final_count = 0
    partial_cpu_seconds = 0.0
    final_cpu_seconds = 0.0

    for chunk in chunks:
        if isinstance(service, StreamingSpeechToTextService):
            preview_started_at = time.perf_counter()
            previews = service.preview_chunk(chunk)
            partial_cpu_seconds += time.perf_counter() - preview_started_at
            for preview in previews:
                text = preview.text.strip()
                if not text:
                    continue
                partial_count += 1
                partial_texts.append(text)
                partial_emit_times.append(time.perf_counter() - benchmark_start)

        for segment in segmenter.split(chunk):
            final_started_at = time.perf_counter()
            result = service.transcribe(segment)
            final_cpu_seconds += time.perf_counter() - final_started_at
            text = result.text.strip()
            if not text:
                continue
            final_count += 1
            final_texts.append(text)
            final_emit_times.append(time.perf_counter() - benchmark_start)

    total_elapsed_seconds = time.perf_counter() - benchmark_start
    final_transcript = " ".join(final_texts).strip()
    partial_transcript = partial_texts[-1] if partial_texts else ""
    result = {
        "backend": backend_name,
        "model_id": model_id,
        "sample_name": sample.name,
        "wav_path": str(sample.wav_path),
        "source": sample.source,
        "audio_duration_seconds": round(audio_duration_seconds, 4),
        "chunk_ms": chunk_ms,
        "partial_count": partial_count,
        "final_count": final_count,
        "first_partial_latency_seconds": _round_or_none(partial_emit_times[0] if partial_emit_times else None),
        "first_final_latency_seconds": _round_or_none(final_emit_times[0] if final_emit_times else None),
        "avg_partial_emit_interval_seconds": _round_or_none(_average_intervals(partial_emit_times)),
        "avg_final_emit_interval_seconds": _round_or_none(_average_intervals(final_emit_times)),
        "partial_cpu_seconds": round(partial_cpu_seconds, 4),
        "final_cpu_seconds": round(final_cpu_seconds, 4),
        "total_elapsed_seconds": round(total_elapsed_seconds, 4),
        "rtf_total": round(total_elapsed_seconds / audio_duration_seconds, 4),
        "rtf_partial_cpu": round(partial_cpu_seconds / audio_duration_seconds, 4),
        "rtf_final_cpu": round(final_cpu_seconds / audio_duration_seconds, 4),
        "last_partial_transcript": partial_transcript,
        "final_transcript": final_transcript,
    }
    if sample.reference_text:
        result["reference_text"] = sample.reference_text
        result["wer_final"] = compute_word_error_rate(sample.reference_text, final_transcript).__dict__
        result["cer_final"] = compute_character_error_rate(sample.reference_text, final_transcript).__dict__
    return result


def _run_warmup(service, sample: RealtimeBenchmarkSample, chunk_ms: int) -> None:
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
    source_policy = resolve_audio_source_policy(sample.source, settings)
    segmenter = _build_audio_segmenter(source_policy)
    if chunks and isinstance(service, StreamingSpeechToTextService):
        service.preview_chunk(chunks[0])
    if chunks:
        for segment in segmenter.split(chunks[0]):
            service.transcribe(segment)
            break


def _load_realtime_wrapper_profiles() -> dict[str, RealtimeWrapperProfile]:
    profile_path = PROJECT_ROOT / "backend" / "config" / "realtime_wrapper_profiles.json"
    raw_profiles = json.loads(profile_path.read_text(encoding="utf-8"))
    profiles: dict[str, RealtimeWrapperProfile] = {}
    for backend_name, payload in raw_profiles.items():
        profiles[backend_name] = RealtimeWrapperProfile(
            script_path=(PROJECT_ROOT / payload["script_path"]).resolve(),
            output_format=payload["output_format"],
            default_model_id=payload["default_model_id"],
            language=payload["language"],
            language_arg=payload.get("language_arg", "--language"),
            base_args=tuple(payload["base_args"]),
            model_arg=payload["model_arg"],
        )
    return profiles


def _resolve_wrapper_model_id(
    backend_name: str,
    overrides: dict[str, str],
    profile_backend_name: str,
    profile: RealtimeWrapperProfile,
) -> str:
    return _resolve_override_value(
        backend_name,
        profile_backend_name,
        overrides,
        profile.default_model_id,
    )


def _build_wrapper_subprocess_env() -> dict[str, str]:
    env = os.environ.copy()
    env.setdefault("PYTHONUTF8", "1")
    env["PYTHONIOENCODING"] = "utf-8"
    return env


def _parse_wrapper_output(output_format: str, stdout_text: str) -> dict[str, Any]:
    if output_format == "whisper_out_txt":
        return _parse_whisper_out_txt(stdout_text)
    if output_format == "simul_jsonl":
        return _parse_simulstreaming_jsonl(stdout_text)
    raise ValueError(f"지원하지 않는 wrapper output 형식입니다: {output_format}")


def _parse_whisper_out_txt(stdout_text: str) -> dict[str, Any]:
    final_texts: list[str] = []
    final_emit_times: list[float] = []
    for raw_line in stdout_text.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        parts = line.split(maxsplit=3)
        if len(parts) < 4:
            continue
        emission_ms = float(parts[0])
        text = parts[3].strip()
        if not text:
            continue
        final_emit_times.append(emission_ms / 1000.0)
        final_texts.append(text)

    return {
        "partial_count": 0,
        "final_count": len(final_texts),
        "first_partial_latency_seconds": None,
        "first_final_latency_seconds": final_emit_times[0] if final_emit_times else None,
        "partial_emit_times": [],
        "final_emit_times": final_emit_times,
        "last_partial_transcript": "",
        "final_transcript": " ".join(final_texts).strip(),
    }


def _parse_simulstreaming_jsonl(stdout_text: str) -> dict[str, Any]:
    partial_texts: list[str] = []
    final_texts: list[str] = []
    partial_emit_times: list[float] = []
    final_emit_times: list[float] = []

    for raw_line in stdout_text.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        try:
            payload = json.loads(line)
        except json.JSONDecodeError:
            continue
        if not isinstance(payload, dict):
            continue
        text = str(payload.get("text", "")).strip()
        emission_time = payload.get("emission_time")
        if emission_time is None or not text:
            continue
        emit_seconds = float(emission_time)
        if payload.get("is_final"):
            final_emit_times.append(emit_seconds)
            final_texts.append(text)
        else:
            partial_emit_times.append(emit_seconds)
            partial_texts.append(text)

    return {
        "partial_count": len(partial_texts),
        "final_count": len(final_texts),
        "first_partial_latency_seconds": partial_emit_times[0] if partial_emit_times else None,
        "first_final_latency_seconds": final_emit_times[0] if final_emit_times else None,
        "partial_emit_times": partial_emit_times,
        "final_emit_times": final_emit_times,
        "last_partial_transcript": partial_texts[-1] if partial_texts else "",
        "final_transcript": " ".join(final_texts).strip(),
    }


def _average_intervals(points: list[float]) -> float | None:
    if len(points) < 2:
        return None
    intervals = [points[index] - points[index - 1] for index in range(1, len(points))]
    return statistics.mean(intervals)


def _build_audio_segmenter(source_policy):
    if source_policy.use_vad:
        return VadSpeechSegmenter(
            config=VadSegmenterConfig(
                sample_rate_hz=settings.stt_sample_rate_hz,
                sample_width_bytes=settings.stt_sample_width_bytes,
                channels=settings.stt_channels,
                frame_duration_ms=settings.vad_frame_duration_ms,
                pre_roll_ms=settings.vad_pre_roll_ms,
                post_roll_ms=source_policy.vad_post_roll_ms,
                min_speech_ms=source_policy.vad_min_speech_ms,
                max_segment_ms=source_policy.vad_max_segment_ms,
                min_activation_frames=source_policy.vad_min_activation_frames,
                rms_threshold=source_policy.vad_rms_threshold,
                adaptive_noise_floor_alpha=settings.vad_adaptive_noise_floor_alpha,
                adaptive_threshold_multiplier=source_policy.vad_adaptive_threshold_multiplier,
                active_threshold_ratio=source_policy.vad_active_threshold_ratio,
                min_voiced_ratio=source_policy.vad_min_voiced_ratio,
            )
        )
    return SpeechSegmenter()


def _resolve_reference_text(inline_text: str | None, reference_file: str | None) -> str | None:
    if reference_file:
        return _read_text_file(Path(reference_file).resolve())
    return inline_text


def _read_text_file(path: Path) -> str:
    for encoding in ("utf-8-sig", "utf-8", "cp949"):
        try:
            return path.read_text(encoding=encoding).strip()
        except UnicodeDecodeError:
            continue
    raise RuntimeError(f"정답 텍스트 파일을 읽을 수 없습니다: {path}")


def _resolve_backend_model_id(backend_name: str, overrides: dict[str, str]) -> str:
    if backend_name in overrides:
        return overrides[backend_name]
    return settings.stt_model_id


def _parse_override_map(items: list[str], label: str) -> dict[str, str]:
    overrides: dict[str, str] = {}
    for item in items:
        if "=" not in item:
            raise ValueError(f"{label} 형식은 backend=value 여야 합니다.")
        backend_name, value = item.split("=", 1)
        overrides[backend_name.strip()] = value.strip()
    return overrides


def _parse_repeated_override_map(items: list[str], label: str) -> dict[str, list[str]]:
    overrides: dict[str, list[str]] = {}
    for item in items:
        if "=" not in item:
            raise ValueError(f"{label} 형식은 backend=value 여야 합니다.")
        backend_name, value = item.split("=", 1)
        normalized_backend_name = backend_name.strip()
        overrides.setdefault(normalized_backend_name, []).append(value.strip())
    return overrides


def _split_backend_instance_name(backend_name: str) -> tuple[str, str | None]:
    if "@" not in backend_name:
        return backend_name, None
    profile_backend_name, instance_name = backend_name.split("@", 1)
    return profile_backend_name.strip(), instance_name.strip() or None


def _resolve_override_value(
    backend_name: str,
    profile_backend_name: str,
    overrides: dict[str, str],
    default_value: str,
) -> str:
    if backend_name in overrides:
        return overrides[backend_name]
    if profile_backend_name in overrides:
        return overrides[profile_backend_name]
    return default_value


def _resolve_backend_args(
    backend_name: str,
    profile_backend_name: str,
    overrides: dict[str, list[str]],
) -> list[str]:
    resolved_args: list[str] = []
    if profile_backend_name in overrides:
        resolved_args.extend(overrides[profile_backend_name])
    if backend_name in overrides:
        resolved_args.extend(overrides[backend_name])
    return resolved_args


def _parse_backend_model_overrides(items: list[str]) -> dict[str, str]:
    """기존 테스트와의 호환성을 위한 wrapper."""

    return _parse_override_map(items, "--backend-model")


def _round_or_none(value: float | None) -> float | None:
    if value is None:
        return None
    return round(value, 4)


def _benchmark_backend_subprocess(
    backend_name: str,
    python_exe: str,
    sample: RealtimeBenchmarkSample,
    chunk_ms: int,
    warmup: bool,
    backend_model_overrides: dict[str, str],
) -> dict:
    with tempfile.NamedTemporaryFile(delete=False, suffix=".json") as handle:
        output_path = Path(handle.name)

    command = [
        python_exe,
        str(Path(__file__).resolve()),
        "--wav",
        str(sample.wav_path),
        "--name",
        sample.name,
        "--source",
        sample.source,
        "--backend",
        backend_name,
        "--chunk-ms",
        str(chunk_ms),
        "--output-json",
        str(output_path),
    ]
    if sample.reference_text:
        command.extend(["--reference-text", sample.reference_text])
    if backend_name in backend_model_overrides:
        command.extend(["--backend-model", f"{backend_name}={backend_model_overrides[backend_name]}"])
    if warmup:
        command.append("--warmup")

    env = os.environ.copy()
    env["CAPS_BENCHMARK_FORCE_LOCAL"] = "1"

    try:
        completed = subprocess.run(
            command,
            cwd=str(PROJECT_ROOT),
            check=False,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            env=env,
        )
        if completed.returncode != 0:
            raise RuntimeError(
                "backend benchmark subprocess failed: "
                f"backend={backend_name} returncode={completed.returncode} "
                f"stdout={completed.stdout.strip()} stderr={completed.stderr.strip()}"
            )
        payload = json.loads(output_path.read_text(encoding="utf-8"))
        return payload["results"][0]
    finally:
        output_path.unlink(missing_ok=True)


def print_summary(results: list[dict]) -> None:
    for item in results:
        if item.get("error"):
            print(
                f"[{item['backend']}] error={item['error']}"
            )
            continue
        print(
            f"[{item['backend']}] model={item['model_id']} "
            f"first_partial={item['first_partial_latency_seconds']} "
            f"first_final={item['first_final_latency_seconds']} "
            f"partial_count={item['partial_count']} "
            f"final_count={item['final_count']} "
            f"rtf_total={item['rtf_total']}"
        )
        if "wer_final" in item:
            print(
                f"  - wer_final={item['wer_final']['rate']} "
                f"cer_final={item['cer_final']['rate']}"
            )


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    sample = load_sample(args)
    backends = args.backends or [settings.stt_backend]
    backend_model_overrides = _parse_override_map(args.backend_models or [], "--backend-model")
    backend_python_overrides = _parse_override_map(args.backend_pythons or [], "--backend-python")
    backend_arg_overrides = _parse_repeated_override_map(args.backend_args or [], "--backend-arg")
    force_local = os.environ.get("CAPS_BENCHMARK_FORCE_LOCAL") == "1"
    wrapper_profiles = _load_realtime_wrapper_profiles()

    results: list[dict] = []
    current_python = str(Path(sys.executable).resolve())
    for backend_name in backends:
        try:
            profile_backend_name, _ = _split_backend_instance_name(backend_name)
            if profile_backend_name in wrapper_profiles:
                results.append(
                    benchmark_wrapper_backend(
                        backend_name=backend_name,
                        sample=sample,
                        backend_model_overrides=backend_model_overrides,
                        backend_python_overrides=backend_python_overrides,
                        backend_arg_overrides=backend_arg_overrides,
                        wrapper_profiles=wrapper_profiles,
                    )
                )
                continue

            override_python = backend_python_overrides.get(backend_name)
            if override_python and not force_local:
                resolved_override = str(Path(override_python).resolve())
                if resolved_override != current_python:
                    results.append(
                        _benchmark_backend_subprocess(
                            backend_name=backend_name,
                            python_exe=resolved_override,
                            sample=sample,
                            chunk_ms=args.chunk_ms,
                            warmup=args.warmup,
                            backend_model_overrides=backend_model_overrides,
                        )
                    )
                    continue

                results.append(
                    benchmark_backend(
                        backend_name=backend_name,
                        sample=sample,
                        chunk_ms=args.chunk_ms,
                        warmup=args.warmup,
                        backend_model_overrides=backend_model_overrides,
                    )
                )
            else:
                results.append(
                    benchmark_backend(
                        backend_name=backend_name,
                        sample=sample,
                        chunk_ms=args.chunk_ms,
                        warmup=args.warmup,
                        backend_model_overrides=backend_model_overrides,
                    )
                )
        except Exception as error:  # pragma: no cover - benchmark loop safety net
            results.append(
                {
                    "backend": backend_name,
                    "model_id": backend_model_overrides.get(backend_name, ""),
                    "sample_name": sample.name,
                    "wav_path": str(sample.wav_path),
                    "source": sample.source,
                    "error": str(error),
                }
            )

    print_summary(results)
    payload = {"results": results}
    if args.output_json:
        output_path = Path(args.output_json).resolve()
        output_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"saved_json={output_path}")
    else:
        print(json.dumps(payload, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()

