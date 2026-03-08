"""sherpa-onnx 기반 로컬 실시간 STT 벤치마크 래퍼."""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[3]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")

from backend.app.services.audio.io.wav_chunk_reader import read_pcm_wave_file, split_pcm_bytes  # noqa: E402


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="sherpa-onnx streaming benchmark wrapper")
    parser.add_argument("wav_path", help="입력 WAV 파일 경로")
    parser.add_argument("--model_path", required=True, help="sherpa-onnx 로컬 모델 디렉터리")
    parser.add_argument("--language", default="ko", help="호환성용 인자. 현재 내부 로직에서는 사용하지 않음")
    parser.add_argument("--provider", default="cpu", choices=["cpu", "cuda"], help="onnxruntime provider")
    parser.add_argument("--num-threads", type=int, default=2, help="추론 스레드 수")
    parser.add_argument("--chunk-ms", type=int, default=120, help="입력 청크 길이(ms)")
    parser.add_argument("--sample-rate", type=int, default=16000, help="기본 샘플레이트")
    parser.add_argument(
        "--decoding-method",
        default="greedy_search",
        choices=["greedy_search", "modified_beam_search"],
        help="온라인 디코딩 방식",
    )
    parser.add_argument("--max-active-paths", type=int, default=4, help="modified beam search 활성 경로 수")
    parser.add_argument("--enable-endpoint-detection", action="store_true", help="endpoint detection 활성화")
    parser.add_argument("--rule1-min-trailing-silence", type=float, default=2.4, help="endpoint rule1 trailing silence")
    parser.add_argument("--rule2-min-trailing-silence", type=float, default=1.2, help="endpoint rule2 trailing silence")
    parser.add_argument("--rule3-min-utterance-length", type=float, default=20.0, help="endpoint rule3 최소 발화 길이")
    return parser


def resolve_transducer_artifacts(model_dir: Path) -> dict[str, Path]:
    candidates = {
        "tokens": ("tokens.txt",),
        "encoder": ("encoder*.onnx",),
        "decoder": ("decoder*.onnx",),
        "joiner": ("joiner*.onnx",),
    }
    resolved: dict[str, Path] = {}
    for key, patterns in candidates.items():
        for pattern in patterns:
            matches = _sort_artifact_matches(key, model_dir.glob(pattern))
            if matches:
                resolved[key] = matches[0].resolve()
                break
        if key not in resolved:
            raise RuntimeError(f"sherpa-onnx 모델 파일을 찾지 못했습니다: key={key} dir={model_dir}")
    return resolved


def _sort_artifact_matches(key: str, matches) -> list[Path]:
    paths = [path.resolve() for path in matches]

    def sort_key(path: Path) -> tuple[int, str]:
        name = path.name.casefold()
        is_int8 = ".int8." in name
        if key == "decoder":
            return (1 if is_int8 else 0, name)
        if key in {"encoder", "joiner"}:
            return (0 if is_int8 else 1, name)
        return (0, name)

    return sorted(paths, key=sort_key)


def create_recognizer(
    model_dir: Path,
    provider: str,
    num_threads: int,
    sample_rate: int,
    decoding_method: str,
    max_active_paths: int,
    enable_endpoint_detection: bool,
    rule1_min_trailing_silence: float,
    rule2_min_trailing_silence: float,
    rule3_min_utterance_length: float,
):
    try:
        import sherpa_onnx
    except ImportError as error:
        raise RuntimeError("sherpa-onnx backend를 사용하려면 sherpa-onnx 패키지를 설치해야 합니다.") from error

    artifacts = resolve_transducer_artifacts(model_dir)
    return sherpa_onnx.OnlineRecognizer.from_transducer(
        tokens=str(artifacts["tokens"]),
        encoder=str(artifacts["encoder"]),
        decoder=str(artifacts["decoder"]),
        joiner=str(artifacts["joiner"]),
        num_threads=num_threads,
        sample_rate=sample_rate,
        provider=provider,
        decoding_method=decoding_method,
        max_active_paths=max_active_paths,
        enable_endpoint_detection=enable_endpoint_detection,
        rule1_min_trailing_silence=rule1_min_trailing_silence,
        rule2_min_trailing_silence=rule2_min_trailing_silence,
        rule3_min_utterance_length=rule3_min_utterance_length,
    )


def emit_payload(*, text: str, is_final: bool, started_at: float) -> None:
    payload = {
        "text": text,
        "is_final": is_final,
        "emission_time": round(time.perf_counter() - started_at, 4),
    }
    print(json.dumps(payload, ensure_ascii=False), flush=True)


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()

    model_dir = Path(args.model_path).resolve()
    recognizer = create_recognizer(
        model_dir=model_dir,
        provider=args.provider,
        num_threads=args.num_threads,
        sample_rate=args.sample_rate,
        decoding_method=args.decoding_method,
        max_active_paths=args.max_active_paths,
        enable_endpoint_detection=args.enable_endpoint_detection,
        rule1_min_trailing_silence=args.rule1_min_trailing_silence,
        rule2_min_trailing_silence=args.rule2_min_trailing_silence,
        rule3_min_utterance_length=args.rule3_min_utterance_length,
    )
    stream = recognizer.create_stream()

    wave_audio = read_pcm_wave_file(
        args.wav_path,
        expected_sample_rate_hz=args.sample_rate,
        expected_sample_width_bytes=2,
        expected_channels=1,
    )
    chunks = split_pcm_bytes(
        wave_audio.raw_bytes,
        sample_rate_hz=wave_audio.sample_rate_hz,
        sample_width_bytes=wave_audio.sample_width_bytes,
        channels=wave_audio.channels,
        chunk_duration_ms=args.chunk_ms,
    )

    import numpy as np

    started_at = time.perf_counter()
    last_partial_text = ""

    for chunk in chunks:
        # sherpa-onnx는 float32 / [-1.0, 1.0] 스케일 입력을 기대한다.
        audio = np.frombuffer(chunk, dtype=np.int16).astype(np.float32) / 32768.0
        stream.accept_waveform(args.sample_rate, audio)

        while recognizer.is_ready(stream):
            recognizer.decode_stream(stream)

        current_text = recognizer.get_result(stream).strip()
        if current_text and current_text != last_partial_text:
            last_partial_text = current_text
            emit_payload(text=current_text, is_final=False, started_at=started_at)

        if args.enable_endpoint_detection and recognizer.is_endpoint(stream):
            final_text = recognizer.get_result(stream).strip()
            if final_text:
                emit_payload(text=final_text, is_final=True, started_at=started_at)
            recognizer.reset(stream)
            last_partial_text = ""

    stream.input_finished()
    while recognizer.is_ready(stream):
        recognizer.decode_stream(stream)

    final_text = recognizer.get_result(stream).strip()
    if final_text:
        emit_payload(text=final_text, is_final=True, started_at=started_at)


if __name__ == "__main__":
    main()

