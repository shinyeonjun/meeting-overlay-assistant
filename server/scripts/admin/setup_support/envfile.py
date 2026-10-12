"""서버 .env 파일을 읽고 쓰고 현재 프로세스 환경에 반영한다."""

from __future__ import annotations

import os

from server.scripts.admin.setup_support.config import SetupConfig


def _read_env_values(cfg: SetupConfig) -> dict[str, str]:
    source_path = cfg.env_path if cfg.env_path.exists() else cfg.env_example_path
    if not source_path.exists():
        return {}

    values: dict[str, str] = {}
    for line in source_path.read_text(encoding="utf-8-sig", errors="replace").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        values[key.strip()] = value.strip()
    return values


def _write_env_values(cfg: SetupConfig, updates: dict[str, str]) -> list[str]:
    path = cfg.env_path
    source_path = path if path.exists() else cfg.env_example_path
    if source_path.exists():
        lines = source_path.read_text(encoding="utf-8-sig", errors="replace").splitlines()
    else:
        lines = []

    remaining = {key: value for key, value in updates.items() if value is not None}
    written: list[str] = []
    rendered: list[str] = []

    for line in lines:
        if "=" in line and not line.lstrip().startswith("#"):
            key, _value = line.split("=", 1)
            key = key.strip()
            if key in remaining:
                rendered.append(f"{key}={remaining.pop(key)}")
                written.append(key)
                continue
        rendered.append(line)

    if remaining:
        if rendered and rendered[-1].strip():
            rendered.append("")
        rendered.append("# server-admin settings")
        for key, value in remaining.items():
            rendered.append(f"{key}={value}")
            written.append(key)

    path.write_text("\n".join(rendered).rstrip() + "\n", encoding="utf-8")
    return written


def _apply_env_overrides(updates: dict[str, str]) -> None:
    for key, value in updates.items():
        os.environ[key] = value
