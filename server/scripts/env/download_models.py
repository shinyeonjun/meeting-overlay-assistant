"""로컬 STT 모델을 server/models/stt 아래로 내려받는다.

사용 예:
    python server/scripts/env/download_models.py            # 기본 모델 전체
    python server/scripts/env/download_models.py sherpa     # 일부만
    python server/scripts/env/download_models.py --list

Ollama 모델(qwen2.5:3b-instruct, nomic-embed-text 등)은 `ollama pull`로 따로 받는다.
"""

from __future__ import annotations

import argparse
import sys
from dataclasses import dataclass
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[3]
STT_MODELS_DIR = ROOT_DIR / "server" / "models" / "stt"


@dataclass(frozen=True)
class ModelSpec:
    key: str
    repo_id: str
    local_dir: str
    description: str
    allow_patterns: tuple[str, ...] | None = None


MODELS: tuple[ModelSpec, ...] = (
    ModelSpec(
        key="sherpa",
        repo_id="k2-fsa/sherpa-onnx-streaming-zipformer-korean-2024-06-16",
        local_dir="sherpa-onnx-streaming-zipformer-korean-2024-06-16",
        description="실시간 partial STT (system_audio hybrid)",
        # encoder/joiner는 int8, decoder는 fp32를 우선 사용한다 (sherpa/artifacts.py).
        allow_patterns=(
            "tokens.txt",
            "encoder-*.int8.onnx",
            "joiner-*.int8.onnx",
            "decoder-*-avg-1.onnx",
        ),
    ),
    ModelSpec(
        key="turbo",
        repo_id="deepdml/faster-whisper-large-v3-turbo-ct2",
        local_dir="faster-whisper-large-v3-turbo-ct2",
        description="실시간 final / mic STT (faster-whisper)",
    ),
    ModelSpec(
        key="large-v3",
        repo_id="Systran/faster-whisper-large-v3",
        local_dir="faster-whisper-large-v3",
        description="회의 후 노트 재전사 STT (faster-whisper)",
    ),
)


def download(spec: ModelSpec) -> Path:
    from huggingface_hub import snapshot_download

    target = STT_MODELS_DIR / spec.local_dir
    print(f"[{spec.key}] {spec.repo_id} -> {target}")
    snapshot_download(
        repo_id=spec.repo_id,
        local_dir=target,
        allow_patterns=list(spec.allow_patterns) if spec.allow_patterns else None,
    )
    return target


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="로컬 STT 모델을 server/models/stt 아래로 내려받는다.")
    parser.add_argument("keys", nargs="*", help="받을 모델 key (생략하면 전체)")
    parser.add_argument("--list", action="store_true", help="모델 목록만 출력")
    args = parser.parse_args(argv)

    by_key = {spec.key: spec for spec in MODELS}
    if args.list:
        for spec in MODELS:
            print(f"{spec.key:10} {spec.repo_id:60} {spec.description}")
        return 0

    unknown = [key for key in args.keys if key not in by_key]
    if unknown:
        parser.error(f"알 수 없는 key: {', '.join(unknown)} (가능: {', '.join(by_key)})")

    for spec in [by_key[key] for key in args.keys] or MODELS:
        download(spec)
    return 0


if __name__ == "__main__":
    sys.exit(main())
