"""설정 프로필 저장소: 프로필 파일의 목록·저장·적용·삭제를 담당한다."""

from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path

from server.scripts.admin.setup_support.config import (
    SETTINGS_MANAGED_KEYS,
    SETTINGS_PROFILE_ENV_KEY,
    SetupConfig,
)
from server.scripts.admin.setup_support.envfile import (
    _apply_env_overrides,
    _read_env_values,
    _write_env_values,
)
from server.scripts.admin.setup_support.payloads import current_settings_env_values


def _profile_storage_dir(cfg: SetupConfig) -> Path:
    cfg.profile_dir.mkdir(parents=True, exist_ok=True)
    return cfg.profile_dir


def _normalize_profile_name(name: str) -> str:
    cleaned = re.sub(r'[<>:"/\\|?*]+', "-", name.strip())
    cleaned = cleaned.strip(" .")
    if not cleaned:
        raise ValueError("프로필 이름이 비어 있습니다.")
    return cleaned


def _profile_file_path(cfg: SetupConfig, name: str) -> Path:
    return _profile_storage_dir(cfg) / f"{_normalize_profile_name(name)}.json"


def _profile_payload_from_disk(cfg: SetupConfig, path: Path) -> dict[str, object]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    settings_block = payload.get("settings", {})
    active_profile = str(_read_env_values(cfg).get(SETTINGS_PROFILE_ENV_KEY, "") or "")
    return {
        "name": str(payload.get("name") or path.stem),
        "saved_at": str(payload.get("saved_at") or ""),
        "note": str(payload.get("note") or ""),
        "server_port": str(settings_block.get("SERVER_PORT") or ""),
        "auth_enabled": str(settings_block.get("AUTH_ENABLED") or "").lower(),
        "stt_backend": str(settings_block.get("STT_BACKEND") or ""),
        "stt_device": str(settings_block.get("STT_DEVICE") or ""),
        "report_refiner_backend": str(settings_block.get("REPORT_REFINER_BACKEND") or ""),
        "is_active": active_profile == str(payload.get("name") or path.stem),
        "path": str(path),
    }


def _list_settings_profiles(cfg: SetupConfig) -> list[dict[str, object]]:
    profile_dir = _profile_storage_dir(cfg)
    profiles: list[dict[str, object]] = []
    for path in sorted(profile_dir.glob("*.json")):
        try:
            profiles.append(_profile_payload_from_disk(cfg, path))
        except Exception:  # noqa: BLE001
            profiles.append(
                {
                    "name": path.stem,
                    "saved_at": "",
                    "note": "프로필 파일을 읽지 못했습니다.",
                    "server_port": "",
                    "auth_enabled": "",
                    "stt_backend": "",
                    "stt_device": "",
                    "report_refiner_backend": "",
                    "is_active": False,
                    "path": str(path),
                }
            )
    return profiles


def _save_settings_profile(cfg: SetupConfig, name: str, *, note: str | None = None) -> dict[str, object]:
    normalized = _normalize_profile_name(name)
    profile_path = _profile_file_path(cfg, normalized)
    settings_values = current_settings_env_values(cfg)
    settings_values[SETTINGS_PROFILE_ENV_KEY] = normalized
    profile_document = {
        "name": normalized,
        "saved_at": datetime.now(timezone.utc).isoformat(),
        "note": note or "",
        "settings": settings_values,
    }
    profile_path.write_text(json.dumps(profile_document, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return _profile_payload_from_disk(cfg, profile_path)


def _apply_settings_profile(cfg: SetupConfig, name: str) -> dict[str, object]:
    profile_path = _profile_file_path(cfg, name)
    if not profile_path.exists():
        raise ValueError(f"프로필을 찾지 못했습니다: {name}")

    profile_document = json.loads(profile_path.read_text(encoding="utf-8"))
    settings_values = {
        key: str(value)
        for key, value in dict(profile_document.get("settings", {})).items()
        if key in SETTINGS_MANAGED_KEYS
    }
    settings_values[SETTINGS_PROFILE_ENV_KEY] = str(profile_document.get("name") or profile_path.stem)
    _write_env_values(cfg, settings_values)
    _apply_env_overrides(settings_values)
    return _profile_payload_from_disk(cfg, profile_path)


def _delete_settings_profile(cfg: SetupConfig, name: str) -> bool:
    profile_path = _profile_file_path(cfg, name)
    if not profile_path.exists():
        raise ValueError(f"프로필을 찾지 못했습니다: {name}")
    profile_path.unlink()
    return True
