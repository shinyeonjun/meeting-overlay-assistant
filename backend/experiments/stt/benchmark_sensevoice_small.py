"""SenseVoice-Small 기반 pseudo-streaming 벤치마크 래퍼."""

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
    parser = argparse.ArgumentParser(description="SenseVoice-Small pseudo-streaming benchmark wrapper")
    parser.add_argument("wav_path", help="입력 WAV 파일 경로")
    parser.add_argument("--model_path", required=True, help="SenseVoice-Small 로컬 모델 디렉터리")
    parser.add_argument("--language", default="ko", help="SenseVoice 언어 코드")
    parser.add_argument("--device", default="cpu", help="추론 장치 예: cpu, cuda:0")
    parser.add_argument("--chunk-ms", type=int, default=120, help="누적 재전사 단위 청크 길이(ms)")
    parser.add_argument("--sample-rate", type=int, default=16000, help="기대 샘플레이트")
    return parser


def create_model(model_dir: Path, device: str):
    try:
        from funasr import AutoModel
        from funasr.utils.postprocess_utils import rich_transcription_postprocess
    except ImportError as error:
        raise RuntimeError(
            "SenseVoice-Small 벤치마크를 실행하려면 funasr 패키지가 필요합니다."
        ) from error

    model = AutoModel(
        model=str(model_dir),
        device=device,
        disable_update=True,
    )
    return model, rich_transcription_postprocess


def emit_payload(*, text: str, is_final: bool, started_at: float) -> None:
    payload = {
        "text": text,
        "is_final": is_final,
        "emission_time": round(time.perf_counter() - started_at, 4),
    }
    print(json.dumps(payload, ensure_ascii=False), flush=True)


def normalize_text(text: str) -> str:
    return " ".join(text.split()).strip()


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()

    model_dir = Path(args.model_path).resolve()
    if not model_dir.exists():
        raise RuntimeError(f"SenseVoice-Small 모델 경로가 존재하지 않습니다: {model_dir}")

    model, rich_transcription_postprocess = create_model(model_dir, args.device)

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
    accumulated = bytearray()
    last_partial_text = ""

    for chunk in chunks:
        accumulated.extend(chunk)
        audio = np.frombuffer(accumulated, dtype=np.int16).astype(np.float32) / 32768.0
        result = model.generate(
            input=audio,
            cache={},
            language=args.language,
            use_itn=False,
            merge_vad=False,
            batch_size_s=0,
        )
        if not result:
            continue

        current_text = normalize_text(rich_transcription_postprocess(result[0].get("text", "")))
        if current_text and current_text != last_partial_text:
            last_partial_text = current_text
            emit_payload(text=current_text, is_final=False, started_at=started_at)

    if last_partial_text:
        emit_payload(text=last_partial_text, is_final=True, started_at=started_at)


if __name__ == "__main__":
    main()

