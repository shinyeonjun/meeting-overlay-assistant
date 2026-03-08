"""Moonshine ONNX 모델이 Ryzen AI VitisAIExecutionProvider에 얼마나 타는지 확인한다."""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[3]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from backend.app.services.audio.stt.ryzenai_runtime import build_runtime_error_message, inspect_runtime  # noqa: E402


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Moonshine ONNX의 VitisAI provider 적재 가능성을 점검합니다.")
    parser.add_argument("--model-path", required=True, help="Moonshine ONNX 파일 또는 디렉터리 경로")
    parser.add_argument(
        "--provider",
        default="VitisAIExecutionProvider",
        help="우선 시도할 provider 이름",
    )
    parser.add_argument(
        "--ryzen-ai-installation-path",
        help="Ryzen AI 설치 경로. 미지정 시 자동 탐지",
    )
    parser.add_argument(
        "--input-shape",
        action="append",
        dest="input_shapes",
        default=[],
        help="입력 shape override. 형식: input_name=1,80,3000",
    )
    parser.add_argument("--output-json", help="결과를 저장할 JSON 경로")
    return parser


def resolve_model_path(raw_path: str) -> Path:
    candidate = Path(raw_path).resolve()
    if candidate.is_file():
        return candidate
    if not candidate.exists():
        raise FileNotFoundError(f"모델 경로를 찾을 수 없습니다: {candidate}")
    prioritized_names = (
        "encoder_model.onnx",
        "decoder_model.onnx",
        "model.onnx",
    )
    for name in prioritized_names:
        found = list(candidate.rglob(name))
        if found:
            return found[0]
    onnx_files = sorted(candidate.rglob("*.onnx"))
    if not onnx_files:
        raise FileNotFoundError(f"ONNX 파일을 찾을 수 없습니다: {candidate}")
    return onnx_files[0]


def prepare_runtime_environment(installation_path: Path | None) -> list[Any]:
    handles: list[Any] = []
    if installation_path is None or os.name != "nt":
        return handles
    candidate_dirs = [
        installation_path / "deployment",
        installation_path / "onnxruntime" / "bin",
        installation_path / "voe-4.0-win_amd64",
    ]
    for path in candidate_dirs:
        if not path.exists():
            continue
        path_str = str(path)
        if path_str not in os.environ.get("PATH", ""):
            os.environ["PATH"] = f"{path_str};{os.environ.get('PATH', '')}"
        if hasattr(os, "add_dll_directory"):
            handles.append(os.add_dll_directory(path_str))
    return handles


def parse_input_shape_overrides(items: list[str]) -> dict[str, tuple[int, ...]]:
    overrides: dict[str, tuple[int, ...]] = {}
    for item in items:
        if "=" not in item:
            raise ValueError("--input-shape 형식은 input_name=1,80,3000 이어야 합니다.")
        name, values = item.split("=", 1)
        dims = tuple(int(value.strip()) for value in values.split(",") if value.strip())
        overrides[name.strip()] = dims
    return overrides


def build_dummy_inputs(session, shape_overrides: dict[str, tuple[int, ...]]) -> dict[str, Any]:
    import numpy as np

    dtype_map = {
        "tensor(float)": np.float32,
        "tensor(float16)": np.float16,
        "tensor(double)": np.float64,
        "tensor(int64)": np.int64,
        "tensor(int32)": np.int32,
        "tensor(bool)": np.bool_,
    }
    feeds: dict[str, Any] = {}
    for tensor in session.get_inputs():
        dtype = dtype_map.get(tensor.type, np.float32)
        shape = shape_overrides.get(tensor.name) or infer_dummy_shape(tensor.shape, tensor.name)
        feeds[tensor.name] = np.zeros(shape, dtype=dtype)
    return feeds


def infer_dummy_shape(shape: list[Any] | tuple[Any, ...], input_name: str) -> tuple[int, ...]:
    inferred: list[int] = []
    for index, dim in enumerate(shape):
        if isinstance(dim, int) and dim > 0:
            inferred.append(dim)
            continue
        lowered_name = input_name.lower()
        if index == 0:
            inferred.append(1)
        elif "feature" in lowered_name or lowered_name in {"x", "input_features"}:
            inferred.append(80 if index == 1 else 300)
        elif "audio" in lowered_name or "wave" in lowered_name:
            inferred.append(16000)
        else:
            inferred.append(1)
    return tuple(max(value, 1) for value in inferred) or (1,)


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    model_path = resolve_model_path(args.model_path)
    runtime_status = inspect_runtime(args.ryzen_ai_installation_path)
    if not runtime_status.is_ready:
        raise RuntimeError(build_runtime_error_message(runtime_status))

    prepare_runtime_environment(runtime_status.installation_path)

    import onnxruntime as ort

    available_providers = ort.get_available_providers()
    requested_providers = [args.provider, "CPUExecutionProvider"]
    provider_options = [{}, {}]

    session_started_at = time.perf_counter()
    session = ort.InferenceSession(
        str(model_path),
        providers=requested_providers,
        provider_options=provider_options,
    )
    session_init_seconds = time.perf_counter() - session_started_at

    shape_overrides = parse_input_shape_overrides(args.input_shapes)
    dummy_feeds = build_dummy_inputs(session, shape_overrides)
    dry_run_error: str | None = None
    inference_seconds: float | None = None
    output_shapes: list[dict[str, Any]] = []

    try:
        inference_started_at = time.perf_counter()
        outputs = session.run(None, dummy_feeds)
        inference_seconds = time.perf_counter() - inference_started_at
        for index, output in enumerate(outputs):
            shape = list(getattr(output, "shape", []))
            output_shapes.append({"index": index, "shape": shape})
    except Exception as error:  # noqa: BLE001
        dry_run_error = str(error)

    payload = {
        "model_path": str(model_path),
        "available_providers": available_providers,
        "requested_providers": requested_providers,
        "session_providers": session.get_providers(),
        "session_init_seconds": round(session_init_seconds, 4),
        "inputs": [
            {
                "name": tensor.name,
                "type": tensor.type,
                "shape": list(tensor.shape),
                "dummy_shape": list(dummy_feeds[tensor.name].shape),
            }
            for tensor in session.get_inputs()
        ],
        "outputs": output_shapes,
        "inference_seconds": round(inference_seconds, 4) if inference_seconds is not None else None,
        "dry_run_error": dry_run_error,
    }

    text = json.dumps(payload, ensure_ascii=False, indent=2)
    if args.output_json:
        output_path = Path(args.output_json).resolve()
        output_path.write_text(text, encoding="utf-8")
        print(f"saved_json={output_path}")
    print(text)


if __name__ == "__main__":
    main()

