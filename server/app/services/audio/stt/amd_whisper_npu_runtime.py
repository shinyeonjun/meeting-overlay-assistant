"""오디오 영역의 amd whisper npu runtime 서비스를 제공한다."""
from __future__ import annotations

import os
from pathlib import Path
from typing import Any


class AMDWhisperNPURuntimeHelper:
    """AMD Whisper NPU 런타임 경로와 provider 옵션을 관리한다."""

    def __init__(
        self,
        *,
        model_id: str,
        installation_path: Path | None,
        base_model_id: str | None,
        project_root: Path,
    ) -> None:
        self._model_id = model_id
        self._installation_path = installation_path
        self._base_model_id = base_model_id
        self._project_root = project_root

    def build_vitis_provider_options(self, component: str) -> dict[str, str]:
        """Vitis AI provider 설정을 구성한다."""
        config_path = self.resolve_component_config_path(component)
        if config_path is None:
            return {}

        cache_dir = self.resolve_cache_dir()
        return {
            "config_file": str(config_path),
            "cache_dir": str(cache_dir),
            "cache_key": self.build_cache_key(component),
        }

    def prepare_runtime_environment(self, dll_directory_handles: list[Any]) -> None:
        """Windows 런타임 DLL 탐색 경로를 준비한다."""
        installation_path = self._installation_path
        if installation_path is None or os.name != "nt":
            return

        candidate_dirs = [
            installation_path / "deployment",
            installation_path / "onnxruntime" / "bin",
            installation_path / "voe-4.0-win_amd64",
        ]
        existing_dirs = [candidate_path for candidate_path in candidate_dirs if candidate_path.exists()]
        for candidate_path in existing_dirs:
            path_str = str(candidate_path)
            self._prepend_path_entry(path_str)
            if hasattr(os, "add_dll_directory"):
                dll_directory_handles.append(os.add_dll_directory(path_str))

    def resolve_component_config_path(self, component: str) -> Path | None:
        """컴포넌트별 Vitis 설정 파일 경로를 찾는다."""
        config_root = self._project_root / "server" / "models" / "stt" / "config"
        config_name = f"vitisai_config_whisper_{component}.json"
        config_path = config_root / config_name
        if config_path.exists():
            return config_path
        return None

    def resolve_cache_dir(self) -> Path:
        """Vitis 캐시 디렉터리를 보장하고 반환한다."""
        cache_dir = self._project_root / "server" / "models" / "stt" / "cache"
        cache_dir.mkdir(parents=True, exist_ok=True)
        return cache_dir

    def build_cache_key(self, component: str) -> str:
        """모델과 컴포넌트 기준의 캐시 키를 만든다."""
        model_key = self.resolve_model_key()
        return f"whisper_{model_key}_{component}"

    def resolve_model_key(self) -> str:
        """model_id를 Vitis 캐시 키용 축약 이름으로 변환한다."""
        model_id = self._model_id.lower()
        if "large-v3-turbo" in model_id or "large-turbo" in model_id:
            return "large_turbo"
        if "large-v3" in model_id:
            return "large_v3"
        if "medium" in model_id:
            return "medium"
        if "base" in model_id:
            return "base"
        return "small"

    def resolve_base_model_id(self) -> str:
        """WhisperProcessor에 넘길 base model id를 결정한다."""
        if self._base_model_id:
            return self._base_model_id

        model_id = self._model_id.lower()
        if "large-v3-turbo" in model_id or "large-turbo" in model_id:
            return "openai/whisper-large-v3-turbo"
        if "large-v3" in model_id:
            return "openai/whisper-large-v3"
        if "medium" in model_id:
            return "openai/whisper-medium"
        if "base" in model_id:
            return "openai/whisper-base"
        return "openai/whisper-small"

    @staticmethod
    def _prepend_path_entry(path_str: str) -> None:
        current_path = os.environ.get("PATH", "")
        current_entries = [entry for entry in current_path.split(os.pathsep) if entry]
        if path_str in current_entries:
            return

        if current_path:
            os.environ["PATH"] = f"{path_str}{os.pathsep}{current_path}"
            return
        os.environ["PATH"] = path_str
