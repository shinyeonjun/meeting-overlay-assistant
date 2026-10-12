"""setup_server 상태·설정·로그 payload를 만든다."""

from __future__ import annotations

from collections import deque
from pathlib import Path

from server.app.api.http.dependencies import (
    get_auth_service,
    get_runtime_monitor_service,
    get_session_service,
)
from server.app.api.http.wiring.persistence import describe_primary_persistence_target
from server.app.core.runtime_readiness import get_runtime_readiness
from server.app.core.workspace_defaults import DEFAULT_WORKSPACE_NAME
from server.scripts.admin.setup_support.config import (
    DEFAULT_LOG_LINES,
    DEFAULT_SERVER_HOST,
    DEFAULT_SERVER_PORT,
    SETTINGS_PROFILE_ENV_KEY,
    SetupConfig,
)
from server.scripts.admin.setup_support.envfile import _read_env_values


def build_status_payload(cfg: SetupConfig) -> dict[str, object]:
    auth_service = get_auth_service()
    user_count = auth_service.count_users()
    members = auth_service.list_workspace_members() if user_count > 0 else []
    workspace_name = members[0].workspace_name if members else DEFAULT_WORKSPACE_NAME
    backend = "postgresql"
    database_ready = bool(cfg.app_settings.postgresql_dsn)
    return {
        "database_backend": backend,
        "database_target": describe_primary_persistence_target(),
        "database_ready": database_ready,
        "auth_enabled": cfg.app_settings.auth_enabled,
        "user_count": user_count,
        "bootstrap_required": user_count == 0,
        "workspace_name": workspace_name,
        "member_count": len(members),
    }


def build_monitor_payload() -> dict[str, object]:
    runtime_snapshot = get_runtime_monitor_service().build_snapshot()
    return {
        "generated_at": runtime_snapshot["generated_at"],
        "active_session_count": get_session_service().count_running_sessions(),
        "readiness": get_runtime_readiness(),
        "audio_pipeline": runtime_snapshot["audio_pipeline"],
    }


def build_logs_payload(cfg: SetupConfig, *, limit: int = DEFAULT_LOG_LINES) -> dict[str, object]:
    limit = max(1, limit)
    lines = _tail_log_lines(cfg.app_settings.log_file_path, limit=limit)
    return {
        "log_file_path": str(cfg.app_settings.log_file_path),
        "exists": cfg.app_settings.log_file_path.exists(),
        "limit": limit,
        "line_count": len(lines),
        "lines": lines,
    }


def build_settings_payload(cfg: SetupConfig) -> dict[str, object]:
    settings = cfg.app_settings
    current = _read_env_values(cfg)
    return {
        "env_path": str(cfg.env_path),
        "profile_dir": str(cfg.profile_dir),
        "active_profile": current.get(SETTINGS_PROFILE_ENV_KEY, ""),
        "server_host": current.get("SERVER_HOST", DEFAULT_SERVER_HOST),
        "server_port": current.get("SERVER_PORT", str(DEFAULT_SERVER_PORT)),
        "auth_enabled": current.get("AUTH_ENABLED", "false"),
        "log_level": current.get("LOG_LEVEL", "INFO"),
        "stt_backend": current.get("STT_BACKEND", settings.stt_backend),
        "stt_system_backend": current.get("STT_BACKEND_SYSTEM_AUDIO", settings.stt_backend_system_audio or ""),
        "stt_model_id": current.get("STT_MODEL_ID", settings.stt_model_id),
        "stt_device": current.get("STT_DEVICE", settings.stt_device),
        "stt_compute_type": current.get("STT_COMPUTE_TYPE", settings.stt_compute_type),
        "stt_preload_on_startup": current.get(
            "STT_PRELOAD_ON_STARTUP", _bool_to_env_value(settings.stt_preload_on_startup)
        ),
        "stt_base_url": current.get("STT_BASE_URL", settings.stt_base_url or ""),
        "stt_encoder_model_path": current.get("STT_ENCODER_MODEL_PATH", settings.stt_encoder_model_path or ""),
        "stt_decoder_model_path": current.get("STT_DECODER_MODEL_PATH", settings.stt_decoder_model_path or ""),
        "analyzer_backend": current.get("ANALYZER_BACKEND", settings.analyzer_backend),
        "ryzen_ai_installation_path": current.get(
            "RYZEN_AI_INSTALLATION_PATH", settings.ryzen_ai_installation_path or ""
        ),
        "speaker_diarizer_backend": current.get("SPEAKER_DIARIZER_BACKEND", settings.speaker_diarizer_backend),
        "speaker_diarizer_device": current.get("SPEAKER_DIARIZER_DEVICE", settings.speaker_diarizer_device),
        "speaker_diarizer_worker_script_path": current.get(
            "SPEAKER_DIARIZER_WORKER_SCRIPT_PATH",
            settings.speaker_diarizer_worker_script_path or "",
        ),
        "llm_base_url": current.get("LLM_BASE_URL", settings.llm_base_url or ""),
        "report_refiner_backend": current.get("REPORT_REFINER_BACKEND", settings.report_refiner_backend),
    }


def current_settings_env_values(cfg: SetupConfig) -> dict[str, str]:
    payload = build_settings_payload(cfg)
    return {
        "SERVER_HOST": str(payload["server_host"]),
        "SERVER_PORT": str(payload["server_port"]),
        "AUTH_ENABLED": str(payload["auth_enabled"]).lower(),
        "LOG_LEVEL": str(payload["log_level"]),
        "STT_BACKEND": str(payload["stt_backend"]),
        "STT_BACKEND_SYSTEM_AUDIO": str(payload["stt_system_backend"]),
        "STT_MODEL_ID": str(payload["stt_model_id"]),
        "STT_DEVICE": str(payload["stt_device"]),
        "STT_COMPUTE_TYPE": str(payload["stt_compute_type"]),
        "STT_PRELOAD_ON_STARTUP": str(payload["stt_preload_on_startup"]).lower(),
        "STT_BASE_URL": str(payload["stt_base_url"]),
        "STT_ENCODER_MODEL_PATH": str(payload["stt_encoder_model_path"]),
        "STT_DECODER_MODEL_PATH": str(payload["stt_decoder_model_path"]),
        "ANALYZER_BACKEND": str(payload["analyzer_backend"]),
        "RYZEN_AI_INSTALLATION_PATH": str(payload["ryzen_ai_installation_path"]),
        "SPEAKER_DIARIZER_BACKEND": str(payload["speaker_diarizer_backend"]),
        "SPEAKER_DIARIZER_DEVICE": str(payload["speaker_diarizer_device"]),
        "SPEAKER_DIARIZER_WORKER_SCRIPT_PATH": str(payload["speaker_diarizer_worker_script_path"]),
        "LLM_BASE_URL": str(payload["llm_base_url"]),
        "REPORT_REFINER_BACKEND": str(payload["report_refiner_backend"]),
        SETTINGS_PROFILE_ENV_KEY: str(payload["active_profile"]),
    }


def member_payload(member) -> dict[str, str | None]:
    return {
        "id": member.id,
        "login_id": member.login_id,
        "display_name": member.display_name,
        "workspace_name": member.workspace_name,
        "workspace_role": member.workspace_role or member.role,
        "job_title": member.job_title,
        "department": member.department,
        "status": member.status,
    }


def _bool_to_env_value(value: object) -> str:
    return "true" if bool(value) else "false"


def _tail_log_lines(path: Path, *, limit: int) -> list[str]:
    if not path.exists():
        return []

    with path.open("r", encoding="utf-8", errors="replace") as handle:
        return [line.rstrip("\r\n") for line in deque(handle, maxlen=max(1, limit))]
