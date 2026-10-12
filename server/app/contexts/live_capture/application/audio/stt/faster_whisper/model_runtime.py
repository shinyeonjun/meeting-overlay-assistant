"""faster-whisper 모델 경로/캐시 유틸리티."""

from __future__ import annotations

import importlib.util
import os
from pathlib import Path
from time import perf_counter
from typing import Any, Callable


def discover_cuda_bin_dirs(nvidia_roots: list[str]) -> list[str]:
    """pip으로 설치된 NVIDIA 패키지(`nvidia/<pkg>/bin`)의 DLL 디렉터리 목록을 찾는다."""

    bin_dirs: list[str] = []
    for root in nvidia_roots:
        for candidate in sorted(Path(root).glob("*/bin")):
            if candidate.is_dir():
                bin_dirs.append(str(candidate))
    return bin_dirs


def register_cuda_runtime_dirs() -> None:
    """ctranslate2가 cuBLAS/cuDNN DLL을 찾도록 NVIDIA 런타임 경로를 등록한다 (Windows 전용).

    시스템에 CUDA Toolkit이 없어도 venv에 설치된 nvidia-*-cu12 휠만으로 GPU 디코드가 동작하게 한다.
    경로가 없으면 아무것도 하지 않는다.
    """

    if os.name != "nt":
        return
    spec = importlib.util.find_spec("nvidia")
    if spec is None or not spec.submodule_search_locations:
        return

    bin_dirs = discover_cuda_bin_dirs(list(spec.submodule_search_locations))
    if not bin_dirs:
        return
    current_path = os.environ.get("PATH", "")
    for bin_dir in bin_dirs:
        if hasattr(os, "add_dll_directory"):
            os.add_dll_directory(bin_dir)
    os.environ["PATH"] = os.pathsep.join(
        [path for path in bin_dirs if path not in current_path.split(os.pathsep)] + [current_path]
    )


def is_valid_model_directory(path: Path) -> bool:
    """faster-whisper 모델 디렉터리 유효성을 검사한다."""

    required_files = (
        "model.bin",
        "config.json",
        "tokenizer.json",
        "vocabulary.json",
    )
    return path.exists() and path.is_dir() and all((path / filename).exists() for filename in required_files)


def resolve_explicit_model_path(
    *,
    model_path: Path | None,
    model_id: str,
    logger,
) -> Path | None:
    """명시적인 model_path를 검증해 반환한다."""

    if model_path is None:
        return None

    path = model_path.resolve()
    if is_valid_model_directory(path):
        return path

    logger.warning(
        "faster-whisper model_path가 유효하지 않아 무시합니다: model=%s path=%s",
        model_id,
        path,
    )
    return None


def resolve_cached_model_path(*, model_id: str, logger) -> Path | None:
    """로컬 faster-whisper 캐시 경로를 찾는다."""

    try:
        from faster_whisper.utils import download_model
    except ImportError:
        return None

    try:
        resolved_path = download_model(
            model_id,
            local_files_only=True,
        )
    except Exception:
        return None

    path = Path(resolved_path).resolve()
    if not is_valid_model_directory(path):
        return None

    logger.debug(
        "faster-whisper 로컬 캐시 경로 사용: model=%s path=%s",
        model_id,
        path,
    )
    return path


def resolve_model_name_or_path(
    *,
    model_id: str,
    explicit_model_path: Path | None,
    cached_model_path: Path | None,
    local_only: bool,
    logger,
) -> str | None:
    """모델 ID 또는 로컬 경로를 우선순위에 맞게 결정한다."""

    if explicit_model_path is not None:
        return str(explicit_model_path)

    if cached_model_path is not None:
        return str(cached_model_path)

    if local_only:
        return None

    logger.warning(
        "faster-whisper 로컬 캐시를 찾지 못해 model_id로 직접 로드합니다: model=%s",
        model_id,
    )
    return model_id


def load_cached_model(
    *,
    config,
    model_name_or_path: str,
    model_cache: dict[tuple[str, str, str, int], Any],
    model_cache_lock,
    load_model_class: Callable[[], Any],
    logger,
):
    """프로세스 전역 캐시를 사용해 모델을 로드한다."""

    cache_key = (
        model_name_or_path,
        config.device,
        config.compute_type,
        config.cpu_threads,
    )
    with model_cache_lock:
        cached_model = model_cache.get(cache_key)
        if cached_model is None:
            model_kwargs: dict[str, Any] = {
                "device": config.device,
                "compute_type": config.compute_type,
            }
            if config.cpu_threads > 0:
                model_kwargs["cpu_threads"] = config.cpu_threads

            started_at = perf_counter()
            logger.info(
                "faster-whisper 모델 로드 시작: model=%s source=%s device=%s compute_type=%s",
                config.model_id,
                model_name_or_path,
                config.device,
                config.compute_type,
            )
            cached_model = load_model_class()(model_name_or_path, **model_kwargs)
            setattr(cached_model, "_caps_model_source", model_name_or_path)
            model_cache[cache_key] = cached_model
            logger.info(
                "faster-whisper 모델 로드 완료: model=%s source=%s elapsed=%.3fs",
                config.model_id,
                model_name_or_path,
                perf_counter() - started_at,
            )
        else:
            logger.debug(
                "faster-whisper 모델 캐시 재사용: model=%s source=%s",
                config.model_id,
                model_name_or_path,
            )
        return cached_model
