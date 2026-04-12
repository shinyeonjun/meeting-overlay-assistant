"""오디오 영역의 runtime 서비스를 제공한다."""
from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from server.app.services.audio.stt.ryzenai_runtime import (
    build_runtime_error_message,
    inspect_runtime,
)


def ensure_runtime_ready(
    *,
    runtime_validated: bool,
    installation_path: Path | None,
    model_id: str,
    prepare_runtime_environment,
    logger,
    inspect_runtime_fn=inspect_runtime,
    build_runtime_error_message_fn=build_runtime_error_message,
) -> bool:
    """Ryzen AI 런타임 준비 상태를 확인한다."""

    if runtime_validated:
        return True

    runtime_status = inspect_runtime_fn(str(installation_path) if installation_path else None)
    if not runtime_status.is_ready:
        raise RuntimeError(build_runtime_error_message_fn(runtime_status))

    prepare_runtime_environment()
    logger.info("AMD Whisper NPU 런타임 준비 완료: model_id=%s", model_id)
    return True


def prepare_runtime_environment(*, installation_path: Path | None, dll_directory_handles: list[Any]) -> None:
    """Windows DLL 경로와 PATH를 준비한다."""

    if installation_path is None or os.name != "nt":
        return

    candidate_dirs = [
        installation_path / "deployment",
        installation_path / "onnxruntime" / "bin",
        installation_path / "voe-4.0-win_amd64",
    ]
    existing_dirs = [path for path in candidate_dirs if path.exists()]
    for path in existing_dirs:
        path_str = str(path)
        if path_str not in os.environ.get("PATH", ""):
            os.environ["PATH"] = f"{path_str};{os.environ.get('PATH', '')}"
        if hasattr(os, "add_dll_directory"):
            handle = os.add_dll_directory(path_str)
            dll_directory_handles.append(handle)


def resolve_component_config_path(*, project_root: Path, component: str) -> Path | None:
    """Vitis AI component config 경로를 찾는다."""

    config_root = project_root / "server" / "models" / "stt" / "config"
    config_name = f"vitisai_config_whisper_{component}.json"
    config_path = config_root / config_name
    if config_path.exists():
        return config_path
    return None


def resolve_cache_dir(*, project_root: Path) -> Path:
    """모델 캐시 디렉터리를 반환한다."""

    cache_dir = project_root / "server" / "models" / "stt" / "cache"
    cache_dir.mkdir(parents=True, exist_ok=True)
    return cache_dir


def resolve_model_key(model_id: str) -> str:
    """모델 ID를 캐시 키용 축약명으로 변환한다."""

    lowered_model_id = model_id.lower()
    if "large-v3-turbo" in lowered_model_id or "large-turbo" in lowered_model_id:
        return "large_turbo"
    if "large-v3" in lowered_model_id:
        return "large_v3"
    if "medium" in lowered_model_id:
        return "medium"
    if "base" in lowered_model_id:
        return "base"
    return "small"


def build_cache_key(*, model_id: str, component: str) -> str:
    """component별 캐시 키를 만든다."""

    return f"whisper_{resolve_model_key(model_id)}_{component}"


def resolve_base_model_id(*, base_model_id: str | None, model_id: str) -> str:
    """Hugging Face base model ID를 추론한다."""

    if base_model_id:
        return base_model_id

    lowered_model_id = model_id.lower()
    if "large-v3-turbo" in lowered_model_id or "large-turbo" in lowered_model_id:
        return "openai/whisper-large-v3-turbo"
    if "large-v3" in lowered_model_id:
        return "openai/whisper-large-v3"
    if "medium" in lowered_model_id:
        return "openai/whisper-medium"
    if "base" in lowered_model_id:
        return "openai/whisper-base"
    return "openai/whisper-small"
