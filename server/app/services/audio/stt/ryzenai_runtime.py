"""Ryzen AI 런타임 진단 유틸리티."""

from __future__ import annotations

import importlib.util
import os
from dataclasses import dataclass
from pathlib import Path


REQUIRED_RUNTIME_FILES = (
    Path("quicktest/quicktest.py"),
    Path("quicktest/test_model.onnx"),
    Path("voe-4.0-win_amd64/vaip_config.json"),
    Path("onnxruntime/bin/onnxruntime.dll"),
)

REQUIRED_PYTHON_MODULES = (
    "onnxruntime",
    "ryzenai_dynamic_dispatch",
    "voe",
)


@dataclass(frozen=True)
class RyzenAIRuntimeStatus:
    """Ryzen AI 런타임 상태."""

    installation_path: Path | None
    missing_files: tuple[Path, ...]
    missing_modules: tuple[str, ...]

    @property
    def is_ready(self) -> bool:
        """런타임이 실제 실행 가능한 상태인지 반환한다."""
        return (
            self.installation_path is not None
            and not self.missing_files
            and not self.missing_modules
        )


def detect_installation_path(explicit_path: str | None = None) -> Path | None:
    """Ryzen AI 설치 경로를 찾는다."""
    candidate = explicit_path or os.getenv("RYZEN_AI_INSTALLATION_PATH")
    if candidate:
        path = Path(candidate)
        return path if path.exists() else None

    root = Path(r"C:\Program Files\RyzenAI")
    if not root.exists():
        return None

    version_dirs = sorted(
        (path for path in root.iterdir() if path.is_dir()),
        key=lambda path: tuple(int(part) if part.isdigit() else part for part in path.name.split(".")),
        reverse=True,
    )
    return version_dirs[0] if version_dirs else None


def inspect_runtime(explicit_path: str | None = None) -> RyzenAIRuntimeStatus:
    """Ryzen AI 런타임 준비 상태를 확인한다."""
    installation_path = detect_installation_path(explicit_path)
    if installation_path is None:
        return RyzenAIRuntimeStatus(
            installation_path=None,
            missing_files=REQUIRED_RUNTIME_FILES,
            missing_modules=_missing_modules(),
        )

    missing_files = tuple(
        relative_path
        for relative_path in REQUIRED_RUNTIME_FILES
        if not (installation_path / relative_path).exists()
    )
    return RyzenAIRuntimeStatus(
        installation_path=installation_path,
        missing_files=missing_files,
        missing_modules=_missing_modules(),
    )


def build_runtime_error_message(status: RyzenAIRuntimeStatus) -> str:
    """사용자에게 바로 보여줄 수 있는 런타임 오류 메시지를 만든다."""
    if status.installation_path is None:
        return (
            "Ryzen AI 설치 경로를 찾지 못했습니다. "
            "RYZEN_AI_INSTALLATION_PATH를 설정하거나 "
            r"'C:\Program Files\RyzenAI\<version>' 설치를 확인하세요."
        )

    details: list[str] = [f"Ryzen AI 설치 경로: {status.installation_path}"]
    if status.missing_files:
        missing = ", ".join(str(path) for path in status.missing_files)
        details.append(f"누락 파일: {missing}")
    if status.missing_modules:
        modules = ", ".join(status.missing_modules)
        details.append(
            "누락 파이썬 모듈: "
            f"{modules}. "
            "server/scripts/env/install_ryzenai_runtime.ps1로 현재 venv에 설치하세요."
        )
    if not status.missing_files and not status.missing_modules:
        details.append("Ryzen AI 런타임은 준비됐습니다. Whisper 모델 경로와 백엔드 설정을 확인하세요.")
    return " | ".join(details)


def _missing_modules() -> tuple[str, ...]:
    return tuple(
        module_name
        for module_name in REQUIRED_PYTHON_MODULES
        if importlib.util.find_spec(module_name) is None
    )
