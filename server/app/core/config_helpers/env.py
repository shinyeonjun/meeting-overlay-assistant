"""환경 변수 로딩과 기본 변환 helper."""

from __future__ import annotations

import os
from pathlib import Path

try:
    from dotenv import load_dotenv
except ImportError:  # pragma: no cover - 선택 의존성
    load_dotenv = None


ROOT_DIR = Path(__file__).resolve().parents[4]
ENV_PATH = ROOT_DIR / ".env"
_ENV_LOADED = False


def ensure_env_loaded() -> None:
    """프로젝트 .env를 한 번만 로드한다."""

    global _ENV_LOADED
    if _ENV_LOADED:
        return
    if load_dotenv is not None and ENV_PATH.exists():
        load_dotenv(ENV_PATH)
    _ENV_LOADED = True


def get_env(name: str, default: str | None = None) -> str | None:
    """빈 문자열을 제외한 환경 변수 값을 반환한다."""

    value = os.getenv(name)
    if value is None or value == "":
        return default
    return value


def get_bool(name: str, default: bool) -> bool:
    """환경 변수를 bool로 변환한다."""

    value = get_env(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def get_int(name: str, default: int) -> int:
    """환경 변수를 int로 변환한다."""

    value = get_env(name)
    if value is None:
        return default
    return int(value)


def get_float(name: str, default: float) -> float:
    """환경 변수를 float로 변환한다."""

    value = get_env(name)
    if value is None:
        return default
    return float(value)


def get_csv(name: str, default: list[str]) -> list[str]:
    """환경 변수를 CSV 목록으로 변환한다."""

    value = get_env(name)
    if value is None:
        return default
    return [item.strip() for item in value.split(",") if item.strip()]


def get_path(name: str, default: str) -> Path:
    """환경 변수를 프로젝트 루트 기준 Path로 변환한다."""

    raw = get_env(name, default) or default
    path = Path(raw)
    if not path.is_absolute():
        path = ROOT_DIR / path
    return path

