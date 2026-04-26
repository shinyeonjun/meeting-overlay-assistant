from __future__ import annotations

import argparse
from collections import deque
from datetime import datetime, timezone
import getpass
import json
import os
import re
import socket
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

from rich.columns import Columns
from rich.console import Console, Group
from rich.panel import Panel
from rich.table import Table
from rich.text import Text


PROJECT_ROOT = Path(__file__).resolve().parents[3]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from server.app.api.http.dependencies import (  # noqa: E402
    get_auth_service,
    get_runtime_monitor_service,
    get_session_service,
)
from server.app.core.config import settings  # noqa: E402
from server.app.core.runtime_readiness import get_runtime_readiness  # noqa: E402
from server.app.core.workspace_defaults import DEFAULT_WORKSPACE_NAME  # noqa: E402
from server.app.api.http.wiring.persistence import (  # noqa: E402
    describe_primary_persistence_target,
    initialize_primary_persistence
)
from server.app.services.auth.auth_service import (  # noqa: E402
    BootstrapConflictError,
    UserNotFoundError,
)


def configure_console_encoding() -> None:
    """직접 실행되는 CLI 경로에서만 콘솔 인코딩을 UTF-8로 맞춘다."""

    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    if hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(encoding="utf-8")


CLI_TITLE = "CAPS SERVER SETUP"
DASHBOARD_TITLE = "CAPS 운영 대시보드"
ROLE_CHOICES = ("owner", "admin", "member", "viewer")
DEFAULT_SERVER_HOST = os.getenv("SERVER_HOST", "127.0.0.1")
DEFAULT_SERVER_PORT = int(os.getenv("SERVER_PORT", "8011"))
DEFAULT_LOG_LINES = 18
ENV_FILE_PATH = PROJECT_ROOT / ".env"
ENV_EXAMPLE_PATH = PROJECT_ROOT / ".env.example"
SETTINGS_PROFILE_DIR = PROJECT_ROOT / "server" / "data" / "settings_profiles"
SETTINGS_PROFILE_ENV_KEY = "SERVER_SETTINGS_PROFILE"
SETTINGS_PRESET_CHOICES = ("cpu-local", "cuda-local", "amd-npu", "api-relay")
SETTINGS_MANAGED_KEYS = (
    "SERVER_HOST",
    "SERVER_PORT",
    "AUTH_ENABLED",
    "LOG_LEVEL",
    "STT_BACKEND",
    "STT_BACKEND_SYSTEM_AUDIO",
    "STT_DEVICE",
    "STT_COMPUTE_TYPE",
    "STT_BASE_URL",
    "STT_MODEL_ID",
    "STT_ENCODER_MODEL_PATH",
    "STT_DECODER_MODEL_PATH",
    "STT_PRELOAD_ON_STARTUP",
    "MIC_SERVER_STT_FALLBACK_ENABLED",
    "MIC_SERVER_STT_PRELOAD_ENABLED",
    "ANALYZER_BACKEND",
    "LIVE_ANALYZER_BACKEND",
    "POST_PROCESSING_ANALYZER_BACKEND",
    "REPORT_ANALYZER_BACKEND",
    "RYZEN_AI_INSTALLATION_PATH",
    "SPEAKER_DIARIZER_BACKEND",
    "SPEAKER_DIARIZER_DEVICE",
    "SPEAKER_DIARIZER_WORKER_SCRIPT_PATH",
    "LLM_BASE_URL",
    "REPORT_REFINER_BACKEND",
    SETTINGS_PROFILE_ENV_KEY,
)
SETTINGS_PROFILE_MAP = {
    "cpu-local": {
        "STT_BACKEND": "faster_whisper_streaming",
        "STT_BACKEND_SYSTEM_AUDIO": "hybrid_local_streaming_sherpa",
        "STT_DEVICE": "cpu",
        "STT_COMPUTE_TYPE": "int8",
        "STT_PRELOAD_ON_STARTUP": "true",
        "MIC_SERVER_STT_FALLBACK_ENABLED": "false",
        "MIC_SERVER_STT_PRELOAD_ENABLED": "false",
        "SPEAKER_DIARIZER_BACKEND": "unknown_speaker",
        "SPEAKER_DIARIZER_DEVICE": "cpu",
        "SPEAKER_DIARIZER_WORKER_SCRIPT_PATH": "server/scripts/workers/pyannote_worker.py",
        "ANALYZER_BACKEND": "rule_based",
        "LIVE_ANALYZER_BACKEND": "noop",
        "POST_PROCESSING_ANALYZER_BACKEND": "rule_based",
        "REPORT_ANALYZER_BACKEND": "rule_based",
        "REPORT_REFINER_BACKEND": "noop",
    },
    "cuda-local": {
        "STT_BACKEND": "faster_whisper_streaming",
        "STT_BACKEND_SYSTEM_AUDIO": "hybrid_local_streaming_sherpa",
        "STT_DEVICE": "cuda",
        "STT_COMPUTE_TYPE": "int8_float16",
        "STT_PRELOAD_ON_STARTUP": "true",
        "MIC_SERVER_STT_FALLBACK_ENABLED": "false",
        "MIC_SERVER_STT_PRELOAD_ENABLED": "false",
        "SPEAKER_DIARIZER_BACKEND": "unknown_speaker",
        "SPEAKER_DIARIZER_DEVICE": "cpu",
        "SPEAKER_DIARIZER_WORKER_SCRIPT_PATH": "server/scripts/workers/pyannote_worker.py",
        "ANALYZER_BACKEND": "rule_based",
        "LIVE_ANALYZER_BACKEND": "noop",
        "POST_PROCESSING_ANALYZER_BACKEND": "rule_based",
        "REPORT_ANALYZER_BACKEND": "rule_based",
        "REPORT_REFINER_BACKEND": "noop",
    },
    "amd-npu": {
        "STT_BACKEND": "amd_whisper_npu",
        "STT_BACKEND_SYSTEM_AUDIO": "hybrid_local_streaming_sherpa",
        "STT_MODEL_ID": "amd/whisper-small-onnx-npu",
        "STT_DEVICE": "auto",
        "STT_COMPUTE_TYPE": "default",
        "STT_PRELOAD_ON_STARTUP": "true",
        "MIC_SERVER_STT_FALLBACK_ENABLED": "false",
        "MIC_SERVER_STT_PRELOAD_ENABLED": "false",
        "SPEAKER_DIARIZER_BACKEND": "unknown_speaker",
        "SPEAKER_DIARIZER_DEVICE": "cpu",
        "SPEAKER_DIARIZER_WORKER_SCRIPT_PATH": "server/scripts/workers/pyannote_worker.py",
        "ANALYZER_BACKEND": "rule_based",
        "LIVE_ANALYZER_BACKEND": "noop",
        "POST_PROCESSING_ANALYZER_BACKEND": "rule_based",
        "REPORT_ANALYZER_BACKEND": "rule_based",
        "REPORT_REFINER_BACKEND": "noop",
    },
    "api-relay": {
        "STT_BACKEND": "openai_compatible_audio",
        "STT_BACKEND_SYSTEM_AUDIO": "openai_compatible_audio",
        "STT_DEVICE": "auto",
        "STT_COMPUTE_TYPE": "default",
        "STT_PRELOAD_ON_STARTUP": "false",
        "MIC_SERVER_STT_FALLBACK_ENABLED": "false",
        "MIC_SERVER_STT_PRELOAD_ENABLED": "false",
        "SPEAKER_DIARIZER_BACKEND": "unknown_speaker",
        "SPEAKER_DIARIZER_DEVICE": "cpu",
        "SPEAKER_DIARIZER_WORKER_SCRIPT_PATH": "server/scripts/workers/pyannote_worker.py",
        "ANALYZER_BACKEND": "rule_based",
        "LIVE_ANALYZER_BACKEND": "noop",
        "POST_PROCESSING_ANALYZER_BACKEND": "rule_based",
        "REPORT_ANALYZER_BACKEND": "rule_based",
        "REPORT_REFINER_BACKEND": "noop",
    },
}


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="CAPS 서버 초기 설정과 워크스페이스 멤버 관리를 돕는 CLI입니다.",
        epilog=(
            "예시:\n"
            "  powershell -ExecutionPolicy Bypass -File .\\scripts\\server-admin.ps1 dashboard\n"
            "  powershell -ExecutionPolicy Bypass -File .\\scripts\\server-admin.ps1 doctor\n"
            "  powershell -ExecutionPolicy Bypass -File .\\scripts\\server-admin.ps1 logs --lines 30\n"
            "  powershell -ExecutionPolicy Bypass -File .\\scripts\\server-admin.ps1 settings --interactive\n"
            "  powershell -ExecutionPolicy Bypass -File .\\scripts\\server-admin.ps1 profiles list\n"
            "  powershell -ExecutionPolicy Bypass -File .\\scripts\\server-admin.ps1 profiles save office-cuda --note \"사내 GPU 서버 기본값\"\n"
            "  powershell -ExecutionPolicy Bypass -File .\\scripts\\server-admin.ps1 status\n"
            "  powershell -ExecutionPolicy Bypass -File .\\scripts\\server-admin.ps1 bootstrap-admin --login-id owner --display-name \"관리자\"\n"
            "  powershell -ExecutionPolicy Bypass -File .\\scripts\\server-admin.ps1 add-member --login-id member --display-name \"홍길동\" --role member\n"
            "  powershell -ExecutionPolicy Bypass -File .\\scripts\\server-admin.ps1 change-member-role --login-id member --role admin\n"
            "  powershell -ExecutionPolicy Bypass -File .\\scripts\\server-admin.ps1 list-members"
        ),
        formatter_class=argparse.RawTextHelpFormatter,
    )
    subparsers = parser.add_subparsers(dest="command", required=True, metavar="command")

    dashboard_parser = subparsers.add_parser(
        "dashboard",
        help="운영자용 대시보드를 엽니다.",
    )
    dashboard_parser.add_argument("--once", action="store_true", help="한 번만 출력하고 종료합니다.")
    dashboard_parser.add_argument("--output", choices=["text", "json"], default="text")
    dashboard_parser.add_argument("--host-address", default=DEFAULT_SERVER_HOST, help="진단 대상 서버 호스트")
    dashboard_parser.add_argument("--port", type=int, default=DEFAULT_SERVER_PORT, help="진단 대상 서버 포트")
    dashboard_parser.add_argument("--log-lines", type=int, default=DEFAULT_LOG_LINES, help="로그 미리보기 줄 수")

    doctor_parser = subparsers.add_parser(
        "doctor",
        help="서버 연결과 기본 상태를 진단합니다.",
    )
    doctor_parser.add_argument("--host-address", default=DEFAULT_SERVER_HOST, help="진단 대상 서버 호스트")
    doctor_parser.add_argument("--port", type=int, default=DEFAULT_SERVER_PORT, help="진단 대상 서버 포트")
    doctor_parser.add_argument("--output", choices=["text", "json"], default="text")

    logs_parser = subparsers.add_parser(
        "logs",
        help="최근 서버 로그를 보거나 follow 모드로 추적합니다.",
    )
    logs_parser.add_argument("--lines", type=int, default=DEFAULT_LOG_LINES, help="표시할 최근 로그 줄 수")
    logs_parser.add_argument("--follow", action="store_true", help="새 로그를 계속 따라갑니다.")
    logs_parser.add_argument("--interval", type=float, default=1.0, help="follow 새로고침 간격(초)")
    logs_parser.add_argument("--output", choices=["text", "json"], default="text")

    status_parser = subparsers.add_parser(
        "status",
        help="현재 서버 상태와 인증 설정을 확인합니다.",
    )
    status_parser.add_argument("--output", choices=["text", "json"], default="text")

    bootstrap_parser = subparsers.add_parser(
        "bootstrap-admin",
        help="초기 관리자 계정을 생성합니다.",
    )
    bootstrap_parser.add_argument("--login-id", required=True, help="관리자 로그인 아이디")
    bootstrap_parser.add_argument("--display-name", required=True, help="화면에 표시할 이름")
    bootstrap_parser.add_argument("--password", help="생략하면 프롬프트에서 안전하게 입력합니다.")
    bootstrap_parser.add_argument("--job-title", help="직급 또는 직책")
    bootstrap_parser.add_argument("--department", help="부서명")
    bootstrap_parser.add_argument("--output", choices=["text", "json"], default="text")

    list_members_parser = subparsers.add_parser(
        "list-members",
        help="기본 워크스페이스 멤버 목록을 조회합니다.",
    )
    list_members_parser.add_argument("--output", choices=["text", "json"], default="text")

    add_member_parser = subparsers.add_parser(
        "add-member",
        help="기본 워크스페이스 멤버를 추가합니다.",
    )
    add_member_parser.add_argument("--login-id", required=True, help="새 멤버 로그인 아이디")
    add_member_parser.add_argument("--display-name", required=True, help="화면 표시 이름")
    add_member_parser.add_argument("--password", help="생략하면 프롬프트에서 안전하게 입력합니다.")
    add_member_parser.add_argument(
        "--role",
        default="member",
        choices=ROLE_CHOICES,
        help="워크스페이스 역할",
    )
    add_member_parser.add_argument("--job-title", help="직급 또는 직책")
    add_member_parser.add_argument("--department", help="부서명")
    add_member_parser.add_argument("--output", choices=["text", "json"], default="text")

    change_role_parser = subparsers.add_parser(
        "change-member-role",
        help="기본 워크스페이스 멤버 역할을 변경합니다.",
    )
    change_role_parser.add_argument("--login-id", required=True, help="대상 멤버 로그인 아이디")
    change_role_parser.add_argument(
        "--role",
        required=True,
        choices=ROLE_CHOICES,
        help="변경할 역할",
    )
    change_role_parser.add_argument("--output", choices=["text", "json"], default="text")

    settings_parser = subparsers.add_parser(
        "settings",
        help="서버 기본 설정과 하드웨어 프리셋을 적용합니다.",
    )
    settings_parser.add_argument("--preset", choices=SETTINGS_PRESET_CHOICES, help="하드웨어/운영 프리셋")
    settings_parser.add_argument("--interactive", action="store_true", help="대화형 설정 마법사를 엽니다.")
    settings_parser.add_argument("--server-host", help="기본 서버 호스트")
    settings_parser.add_argument("--server-port", type=int, help="기본 서버 포트")
    settings_parser.add_argument("--auth-enabled", choices=["true", "false"], help="인증 강제 여부")
    settings_parser.add_argument("--log-level", choices=["DEBUG", "INFO", "WARNING", "ERROR"], help="로그 레벨")
    settings_parser.add_argument("--stt-backend", help="기본 STT backend")
    settings_parser.add_argument("--stt-system-backend", help="system audio용 STT backend")
    settings_parser.add_argument("--stt-device", help="STT device")
    settings_parser.add_argument("--stt-compute-type", help="STT compute type")
    settings_parser.add_argument("--stt-base-url", help="외부 STT API URL")
    settings_parser.add_argument("--ryzen-ai-path", help="RyzenAI 설치 경로")
    settings_parser.add_argument("--speaker-diarizer-backend", help="화자 분리 backend")
    settings_parser.add_argument("--speaker-diarizer-device", help="화자 분리 device")
    settings_parser.add_argument("--llm-base-url", help="LLM API URL")
    settings_parser.add_argument("--report-refiner-backend", help="회의록 정제 backend")
    settings_parser.add_argument("--save-profile", help="설정 적용 후 같이 저장할 프로필 이름")
    settings_parser.add_argument("--output", choices=["text", "json"], default="text")

    profiles_parser = subparsers.add_parser(
        "profiles",
        help="저장된 설정 프로필을 관리합니다.",
    )
    profiles_parser.add_argument(
        "action",
        nargs="?",
        default="list",
        choices=("list", "save", "apply", "delete"),
        help="수행할 프로필 작업",
    )
    profiles_parser.add_argument("name", nargs="?", help="프로필 이름")
    profiles_parser.add_argument("--note", help="프로필 설명 메모")
    profiles_parser.add_argument("--output", choices=["text", "json"], default="text")
    return parser


def build_status_payload() -> dict[str, object]:
    auth_service = get_auth_service()
    user_count = auth_service.count_users()
    members = auth_service.list_workspace_members() if user_count > 0 else []
    workspace_name = members[0].workspace_name if members else DEFAULT_WORKSPACE_NAME
    backend = "postgresql"
    database_ready = bool(settings.postgresql_dsn)
    return {
        "database_backend": backend,
        "database_target": describe_primary_persistence_target(),
        "database_ready": database_ready,
        "auth_enabled": settings.auth_enabled,
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


def build_doctor_payload(
    *,
    host_address: str = DEFAULT_SERVER_HOST,
    port: int = DEFAULT_SERVER_PORT,
) -> dict[str, object]:
    settings_payload = build_settings_payload()
    base_url = f"http://{host_address}:{port}"
    health_data, health_error = _fetch_json(f"{base_url}/health")
    readiness_data, readiness_error = _fetch_json(f"{base_url}/api/v1/runtime/readiness")
    tcp_open = _probe_tcp_port(host_address, port)

    issues: list[str] = []
    checks: list[dict[str, str]] = []
    if not tcp_open:
        issues.append("서버 포트가 열려 있지 않습니다.")
    if health_error is not None:
        issues.append(f"/health 확인 실패: {health_error}")
    if readiness_error is not None:
        issues.append(f"/api/v1/runtime/readiness 확인 실패: {readiness_error}")

    env_path = Path(str(settings_payload["env_path"]))
    env_source = env_path if env_path.exists() else ENV_EXAMPLE_PATH
    checks.append(
        _doctor_check(
            "환경 파일",
            "ok" if env_path.exists() else "warn",
            str(env_source),
        )
    )

    log_file_path = settings.log_file_path
    log_parent = log_file_path.parent
    log_status = "ok" if log_parent.exists() else "warn"
    log_detail = str(log_file_path)
    checks.append(_doctor_check("로그 경로", log_status, log_detail))
    if log_status != "ok":
        issues.append(f"로그 디렉터리가 없습니다: {log_parent}")

    worker_script_raw = str(settings_payload["speaker_diarizer_worker_script_path"] or "").strip()
    if worker_script_raw:
        worker_script_path = _resolve_project_path(worker_script_raw)
        worker_status = "ok" if worker_script_path.exists() else "warn"
        checks.append(_doctor_check("화자 분리 worker", worker_status, str(worker_script_path)))
        if worker_status != "ok":
            issues.append(f"화자 분리 worker 스크립트를 찾지 못했습니다: {worker_script_path}")
    else:
        checks.append(_doctor_check("화자 분리 worker", "pending", "미설정"))

    stt_backend = str(settings_payload["stt_backend"])
    stt_base_url = str(settings_payload["stt_base_url"] or "")
    if stt_backend == "openai_compatible_audio":
        api_status = "ok" if stt_base_url else "fail"
        checks.append(_doctor_check("외부 STT API", api_status, stt_base_url or "미설정"))
        if api_status == "fail":
            issues.append("외부 STT backend를 쓰지만 STT_BASE_URL이 비어 있습니다.")
    else:
        checks.append(_doctor_check("외부 STT API", "pending", "미사용"))

    if stt_backend == "amd_whisper_npu":
        ryzen_path_raw = str(settings_payload["ryzen_ai_installation_path"] or "")
        ryzen_path = Path(ryzen_path_raw) if ryzen_path_raw else None
        ryzen_status = "ok" if ryzen_path and ryzen_path.exists() else "fail"
        checks.append(_doctor_check("RyzenAI 경로", ryzen_status, ryzen_path_raw or "미설정"))
        if ryzen_status == "fail":
            issues.append("amd-npu backend를 쓰지만 RyzenAI 설치 경로를 찾지 못했습니다.")

        encoder_raw = str(settings_payload["stt_encoder_model_path"] or "")
        decoder_raw = str(settings_payload["stt_decoder_model_path"] or "")
        encoder_path = Path(encoder_raw) if encoder_raw else None
        decoder_path = Path(decoder_raw) if decoder_raw else None
        encoder_status = "ok" if encoder_path and encoder_path.exists() else "fail"
        decoder_status = "ok" if decoder_path and decoder_path.exists() else "fail"
        checks.append(_doctor_check("AMD encoder", encoder_status, encoder_raw or "미설정"))
        checks.append(_doctor_check("AMD decoder", decoder_status, decoder_raw or "미설정"))
        if encoder_status == "fail":
            issues.append("STT_ENCODER_MODEL_PATH를 찾지 못했습니다.")
        if decoder_status == "fail":
            issues.append("STT_DECODER_MODEL_PATH를 찾지 못했습니다.")
    else:
        checks.append(_doctor_check("RyzenAI 경로", "pending", "미사용"))
        checks.append(_doctor_check("AMD encoder", "pending", "미사용"))
        checks.append(_doctor_check("AMD decoder", "pending", "미사용"))

    llm_base_url = str(settings_payload["llm_base_url"] or "")
    report_refiner_backend = str(settings_payload["report_refiner_backend"])
    if report_refiner_backend != "noop":
        llm_status = "ok" if llm_base_url else "warn"
        checks.append(_doctor_check("LLM API", llm_status, llm_base_url or "미설정"))
        if llm_status == "warn":
            issues.append("LLM 정제가 활성화됐지만 LLM_BASE_URL이 비어 있습니다.")
    else:
        checks.append(_doctor_check("LLM API", "pending", "미사용"))

    return {
        "base_url": base_url,
        "host_address": host_address,
        "port": port,
        "tcp_open": tcp_open,
        "health_ok": health_data is not None and health_data.get("status") == "ok",
        "health_status": health_data.get("status") if isinstance(health_data, dict) else None,
        "readiness_available": readiness_data is not None,
        "backend_ready": bool(readiness_data.get("backend_ready")) if isinstance(readiness_data, dict) else None,
        "warming": bool(readiness_data.get("warming")) if isinstance(readiness_data, dict) else None,
        "stt_ready": bool(readiness_data.get("stt_ready")) if isinstance(readiness_data, dict) else None,
        "health_error": health_error,
        "readiness_error": readiness_error,
        "checks": checks,
        "settings_profile": settings_payload.get("active_profile"),
        "stt_backend": stt_backend,
        "issues": issues,
    }


def build_dashboard_payload(
    *,
    member_limit: int = 6,
    host_address: str = DEFAULT_SERVER_HOST,
    port: int = DEFAULT_SERVER_PORT,
    log_lines: int = DEFAULT_LOG_LINES,
) -> dict[str, object]:
    auth_service = get_auth_service()
    members = auth_service.list_workspace_members()
    return {
        "status": build_status_payload(),
        "monitor": build_monitor_payload(),
        "doctor": build_doctor_payload(host_address=host_address, port=port),
        "settings": build_settings_payload(),
        "logs": build_logs_payload(limit=log_lines),
        "member_preview": [_member_payload(member) for member in members[:member_limit]],
        "member_total": len(members),
    }


def build_logs_payload(*, limit: int = DEFAULT_LOG_LINES) -> dict[str, object]:
    limit = max(1, limit)
    lines = _tail_log_lines(settings.log_file_path, limit=limit)
    return {
        "log_file_path": str(settings.log_file_path),
        "exists": settings.log_file_path.exists(),
        "limit": limit,
        "line_count": len(lines),
        "lines": lines,
    }


def build_settings_payload() -> dict[str, object]:
    current = _read_env_values(ENV_FILE_PATH)
    return {
        "env_path": str(ENV_FILE_PATH),
        "profile_dir": str(SETTINGS_PROFILE_DIR),
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
        "stt_preload_on_startup": current.get("STT_PRELOAD_ON_STARTUP", _bool_to_env_value(settings.stt_preload_on_startup)),
        "stt_base_url": current.get("STT_BASE_URL", settings.stt_base_url or ""),
        "stt_encoder_model_path": current.get("STT_ENCODER_MODEL_PATH", settings.stt_encoder_model_path or ""),
        "stt_decoder_model_path": current.get("STT_DECODER_MODEL_PATH", settings.stt_decoder_model_path or ""),
        "analyzer_backend": current.get("ANALYZER_BACKEND", settings.analyzer_backend),
        "live_analyzer_backend": current.get("LIVE_ANALYZER_BACKEND", settings.live_analyzer_backend),
        "post_processing_analyzer_backend": current.get(
            "POST_PROCESSING_ANALYZER_BACKEND",
            settings.post_processing_analyzer_backend,
        ),
        "report_analyzer_backend": current.get("REPORT_ANALYZER_BACKEND", settings.report_analyzer_backend),
        "ryzen_ai_installation_path": current.get("RYZEN_AI_INSTALLATION_PATH", settings.ryzen_ai_installation_path or ""),
        "speaker_diarizer_backend": current.get("SPEAKER_DIARIZER_BACKEND", settings.speaker_diarizer_backend),
        "speaker_diarizer_device": current.get("SPEAKER_DIARIZER_DEVICE", settings.speaker_diarizer_device),
        "speaker_diarizer_worker_script_path": current.get(
            "SPEAKER_DIARIZER_WORKER_SCRIPT_PATH",
            settings.speaker_diarizer_worker_script_path or "",
        ),
        "llm_base_url": current.get("LLM_BASE_URL", settings.llm_base_url or ""),
        "report_refiner_backend": current.get("REPORT_REFINER_BACKEND", settings.report_refiner_backend),
    }


def _current_settings_env_values() -> dict[str, str]:
    payload = build_settings_payload()
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
        "LIVE_ANALYZER_BACKEND": str(payload["live_analyzer_backend"]),
        "POST_PROCESSING_ANALYZER_BACKEND": str(payload["post_processing_analyzer_backend"]),
        "REPORT_ANALYZER_BACKEND": str(payload["report_analyzer_backend"]),
        "RYZEN_AI_INSTALLATION_PATH": str(payload["ryzen_ai_installation_path"]),
        "SPEAKER_DIARIZER_BACKEND": str(payload["speaker_diarizer_backend"]),
        "SPEAKER_DIARIZER_DEVICE": str(payload["speaker_diarizer_device"]),
        "SPEAKER_DIARIZER_WORKER_SCRIPT_PATH": str(payload["speaker_diarizer_worker_script_path"]),
        "LLM_BASE_URL": str(payload["llm_base_url"]),
        "REPORT_REFINER_BACKEND": str(payload["report_refiner_backend"]),
        SETTINGS_PROFILE_ENV_KEY: str(payload["active_profile"]),
    }


def _profile_storage_dir() -> Path:
    SETTINGS_PROFILE_DIR.mkdir(parents=True, exist_ok=True)
    return SETTINGS_PROFILE_DIR


def _normalize_profile_name(name: str) -> str:
    cleaned = re.sub(r'[<>:"/\\|?*]+', "-", name.strip())
    cleaned = cleaned.strip(" .")
    if not cleaned:
        raise ValueError("프로필 이름이 비어 있습니다.")
    return cleaned


def _profile_file_path(name: str) -> Path:
    return _profile_storage_dir() / f"{_normalize_profile_name(name)}.json"


def _profile_payload_from_disk(path: Path) -> dict[str, object]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    settings_block = payload.get("settings", {})
    active_profile = str(build_settings_payload().get("active_profile") or "")
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


def _list_settings_profiles() -> list[dict[str, object]]:
    profile_dir = _profile_storage_dir()
    profiles: list[dict[str, object]] = []
    for path in sorted(profile_dir.glob("*.json")):
        try:
            profiles.append(_profile_payload_from_disk(path))
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


def _save_settings_profile(name: str, *, note: str | None = None) -> dict[str, object]:
    normalized = _normalize_profile_name(name)
    profile_path = _profile_file_path(normalized)
    settings_values = _current_settings_env_values()
    settings_values[SETTINGS_PROFILE_ENV_KEY] = normalized
    profile_document = {
        "name": normalized,
        "saved_at": datetime.now(timezone.utc).isoformat(),
        "note": note or "",
        "settings": settings_values,
    }
    profile_path.write_text(json.dumps(profile_document, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return _profile_payload_from_disk(profile_path)


def _apply_settings_profile(name: str) -> dict[str, object]:
    profile_path = _profile_file_path(name)
    if not profile_path.exists():
        raise ValueError(f"프로필을 찾지 못했습니다: {name}")

    profile_document = json.loads(profile_path.read_text(encoding="utf-8"))
    settings_values = {
        key: str(value)
        for key, value in dict(profile_document.get("settings", {})).items()
        if key in SETTINGS_MANAGED_KEYS
    }
    settings_values[SETTINGS_PROFILE_ENV_KEY] = str(profile_document.get("name") or profile_path.stem)
    _write_env_values(ENV_FILE_PATH, settings_values)
    _apply_env_overrides(settings_values)
    return _profile_payload_from_disk(profile_path)


def _delete_settings_profile(name: str) -> bool:
    profile_path = _profile_file_path(name)
    if not profile_path.exists():
        raise ValueError(f"프로필을 찾지 못했습니다: {name}")
    profile_path.unlink()
    return True


def apply_settings(args: argparse.Namespace) -> int:
    console = _build_console()
    if args.interactive or not _has_explicit_settings_args(args):
        updates = _collect_settings_wizard(console)
    else:
        updates = _build_settings_updates_from_args(args)

    if not updates:
        if args.output == "json":
            print(json.dumps({"updated": False, "message": "변경할 설정이 없습니다."}, ensure_ascii=False, indent=2))
            return 0
        console.print(_render_hint_panel("설정", ["변경할 설정이 없습니다."]))
        return 0

    written = _write_env_values(ENV_FILE_PATH, updates)
    _apply_env_overrides(updates)
    payload = build_settings_payload()
    payload["updated_keys"] = written
    save_profile_name = getattr(args, "save_profile", None)
    if save_profile_name:
        profile = _save_settings_profile(
            save_profile_name,
            note=f"settings 명령으로 저장 ({datetime.now().strftime('%Y-%m-%d %H:%M')})",
        )
        payload["saved_profile"] = profile["name"]
    elif updates.get(SETTINGS_PROFILE_ENV_KEY):
        payload["saved_profile"] = updates[SETTINGS_PROFILE_ENV_KEY]

    if args.output == "json":
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        return 0

    console.print(_render_settings_panel(payload))
    console.print()
    console.print(
        _render_hint_panel(
            "다음 단계",
            [
                "powershell -ExecutionPolicy Bypass -File .\\scripts\\server-admin.ps1 doctor",
                "powershell -ExecutionPolicy Bypass -File .\\scripts\\dev-server.ps1",
                "설정을 바꾼 뒤에는 서버 프로세스를 다시 시작하세요.",
            ],
        )
    )
    return 0


def manage_profiles(args: argparse.Namespace) -> int:
    action = args.action
    console = _build_console()

    if action == "list":
        profiles = _list_settings_profiles()
        if args.output == "json":
            print(json.dumps(profiles, ensure_ascii=False, indent=2))
            return 0
        console.print(_render_profiles_panel(profiles, title="저장된 설정 프로필"))
        return 0

    if not args.name:
        _print_error("프로필 이름을 함께 입력해 주세요.")
        return 1

    if action == "save":
        profile = _save_settings_profile(args.name, note=args.note)
        if args.output == "json":
            print(json.dumps(profile, ensure_ascii=False, indent=2))
            return 0
        console.print(_render_profiles_panel([profile], title="프로필 저장 완료"))
        console.print()
        console.print(
            _render_hint_panel(
                "다음 단계",
                [
                    "powershell -ExecutionPolicy Bypass -File .\\scripts\\server-admin.ps1 profiles list",
                    f"powershell -ExecutionPolicy Bypass -File .\\scripts\\server-admin.ps1 profiles apply {profile['name']}",
                ],
            )
        )
        return 0

    if action == "apply":
        try:
            profile = _apply_settings_profile(args.name)
        except ValueError as error:
            _print_error(str(error))
            return 1
        if args.output == "json":
            print(json.dumps(profile, ensure_ascii=False, indent=2))
            return 0
        console.print(_render_profiles_panel([profile], title="프로필 적용 완료"))
        console.print()
        console.print(
            _render_hint_panel(
                "다음 단계",
                [
                    "powershell -ExecutionPolicy Bypass -File .\\scripts\\server-admin.ps1 doctor",
                    "powershell -ExecutionPolicy Bypass -File .\\scripts\\dev-server.ps1",
                    "설정이 바뀐 뒤에는 서버 프로세스를 다시 시작하세요.",
                ],
            )
        )
        return 0

    if action == "delete":
        try:
            deleted = _delete_settings_profile(args.name)
        except ValueError as error:
            _print_error(str(error))
            return 1
        payload = {"deleted": deleted, "name": args.name}
        if args.output == "json":
            print(json.dumps(payload, ensure_ascii=False, indent=2))
            return 0
        console.print(_render_hint_panel("프로필 삭제", [f"{args.name} 프로필을 삭제했습니다."]))
        return 0

    _print_error(f"지원하지 않는 프로필 작업입니다: {action}")
    return 1


def print_status(output_mode: str) -> int:
    payload = build_status_payload()
    if output_mode == "json":
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        return 0

    console = _build_console()
    console.print(_render_status_panel(payload))
    console.print()
    console.print(_render_next_steps_panel(payload))
    return 0


def print_doctor(output_mode: str, *, host_address: str, port: int) -> int:
    payload = build_doctor_payload(host_address=host_address, port=port)
    if output_mode == "json":
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        return 0

    console = _build_console()
    console.print(_render_doctor_panel(payload))
    console.print()
    console.print(_render_doctor_hint_panel(payload))
    return 0


def print_logs(
    output_mode: str,
    *,
    lines: int,
    follow: bool,
    interval: float,
) -> int:
    payload = build_logs_payload(limit=lines)
    if output_mode == "json":
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        return 0

    console = _build_console()
    if not follow:
        console.print(_render_logs_panel(payload))
        return 0

    try:
        while True:
            payload = build_logs_payload(limit=lines)
            console.clear()
            console.print(_render_logs_panel(payload, follow=True, interval=interval))
            time.sleep(max(interval, 0.2))
    except KeyboardInterrupt:
        console.print("\n[bold cyan]로그 추적을 종료합니다.[/bold cyan]")
        return 0


def bootstrap_admin(args: argparse.Namespace) -> int:
    password = args.password or getpass.getpass("초기 관리자 비밀번호: ")
    try:
        user = get_auth_service().provision_initial_admin(
            login_id=args.login_id,
            password=password,
            display_name=args.display_name,
            job_title=args.job_title,
            department=args.department,
        )
    except BootstrapConflictError as error:
        _print_error(str(error))
        return 1
    except ValueError as error:
        _print_error(str(error))
        return 1

    payload = _member_payload(user)
    payload["auth_enabled"] = settings.auth_enabled
    if args.output == "json":
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        return 0

    console = _build_console()
    console.print(_render_result_panel("초기 관리자 생성 완료", payload))
    console.print()
    console.print(
        _render_hint_panel(
            "다음 단계",
            [
                "powershell -ExecutionPolicy Bypass -File .\\scripts\\server-admin.ps1 status",
                "powershell -ExecutionPolicy Bypass -File .\\scripts\\server-admin.ps1 dashboard",
                ".env에서 AUTH_ENABLED=true 설정 후 로그인 흐름 확인",
            ],
        )
    )
    return 0


def list_members(output_mode: str) -> int:
    members = get_auth_service().list_workspace_members()
    payload = [_member_payload(member) for member in members]
    if output_mode == "json":
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        return 0

    console = _build_console()
    console.print(_render_members_panel(payload, title="워크스페이스 멤버 목록", compact=False))
    console.print()
    console.print(
        _render_hint_panel(
            "안내",
            [
                "역할을 바꾸려면 change-member-role 명령을 사용하세요.",
                "운영 상태와 함께 보려면 dashboard 명령을 사용하세요.",
            ],
        )
    )
    return 0


def add_member(args: argparse.Namespace) -> int:
    password = args.password or getpass.getpass("멤버 비밀번호: ")
    try:
        user = get_auth_service().create_workspace_user(
            login_id=args.login_id,
            password=password,
            display_name=args.display_name,
            job_title=args.job_title,
            department=args.department,
            role=args.role,
        )
    except ValueError as error:
        _print_error(str(error))
        return 1

    payload = _member_payload(user)
    if args.output == "json":
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        return 0

    console = _build_console()
    console.print(_render_result_panel("멤버 추가 완료", payload))
    console.print()
    console.print(
        _render_hint_panel(
            "다음 단계",
            [
                "powershell -ExecutionPolicy Bypass -File .\\scripts\\server-admin.ps1 list-members",
                "powershell -ExecutionPolicy Bypass -File .\\scripts\\server-admin.ps1 dashboard",
            ],
        )
    )
    return 0


def change_member_role(args: argparse.Namespace) -> int:
    try:
        user = get_auth_service().change_workspace_member_role(
            login_id=args.login_id,
            role=args.role,
        )
    except UserNotFoundError as error:
        _print_error(str(error))
        return 1
    except ValueError as error:
        _print_error(str(error))
        return 1

    payload = _member_payload(user)
    if args.output == "json":
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        return 0

    console = _build_console()
    console.print(_render_result_panel("멤버 역할 변경 완료", payload))
    console.print()
    console.print(
        _render_hint_panel(
            "다음 단계",
            [
                "powershell -ExecutionPolicy Bypass -File .\\scripts\\server-admin.ps1 list-members",
                "powershell -ExecutionPolicy Bypass -File .\\scripts\\server-admin.ps1 dashboard",
            ],
        )
    )
    return 0


def run_dashboard(args: argparse.Namespace) -> int:
    if args.output == "json":
        payload = build_dashboard_payload(
            host_address=args.host_address,
            port=args.port,
            log_lines=args.log_lines,
        )
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        return 0

    console = _build_console()
    if args.once:
        console.print(
            _render_dashboard_group(
                build_dashboard_payload(
                    host_address=args.host_address,
                    port=args.port,
                    log_lines=args.log_lines,
                )
            )
        )
        return 0

    while True:
        payload = build_dashboard_payload(
            host_address=args.host_address,
            port=args.port,
            log_lines=args.log_lines,
        )
        console.clear()
        console.print(_render_dashboard_group(payload))
        console.print()
        action = input(
            "선택 [R 새로고침 / 1 관리자 생성 / 2 멤버 추가 / 3 역할 변경 / 4 멤버 전체 보기 / 5 doctor / 6 live logs / 7 settings / 8 profiles / Q 종료]: "
        ).strip().lower()

        if action in {"", "r"}:
            continue
        if action == "1":
            _dashboard_bootstrap_admin(console)
            continue
        if action == "2":
            _dashboard_add_member(console)
            continue
        if action == "3":
            _dashboard_change_member_role(console)
            continue
        if action == "4":
            _dashboard_show_all_members(console)
            continue
        if action == "5":
            _dashboard_show_doctor(console, host_address=args.host_address, port=args.port)
            continue
        if action == "6":
            _dashboard_show_logs(console, lines=args.log_lines)
            continue
        if action == "7":
            _dashboard_settings(console)
            continue
        if action == "8":
            _dashboard_profiles(console)
            continue
        if action == "q":
            console.print("[bold cyan]대시보드를 종료합니다.[/bold cyan]")
            return 0

        _pause(console, f"알 수 없는 선택입니다: {action}")


def print_dashboard_snapshot(output_mode: str) -> int:
    payload = build_dashboard_payload()
    if output_mode == "json":
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        return 0

    _build_console().print(_render_dashboard_group(payload))
    return 0


def _render_dashboard_group(payload: dict[str, object]) -> Group:
    status = payload["status"]
    monitor = payload["monitor"]
    doctor = payload["doctor"]
    settings_payload = payload["settings"]
    logs = payload["logs"]
    members = payload["member_preview"]
    header = Panel.fit(
        Group(
            Text(DASHBOARD_TITLE, style="bold cyan"),
            Text("운영 상태, 멤버 관리, 실시간 모니터를 한 화면에서 봅니다.", style="dim"),
        ),
        border_style="cyan",
    )
    banner = _render_status_banner(status, doctor)

    summary = Columns(
        [
            _render_overview_panel(status, monitor),
            _render_doctor_panel(doctor),
            _render_settings_summary_panel(settings_payload),
        ],
        expand=True,
        equal=True,
    )
    lower = Columns(
        [
            _render_audio_monitor_panel(monitor["audio_pipeline"], monitor["readiness"]),
            _render_members_panel(members, title=f"멤버 미리보기 ({payload['member_total']}명)", compact=True),
        ],
        expand=True,
        equal=True,
    )
    actions = _render_actions_panel(logs)
    return Group(header, banner, summary, lower, actions)


def _render_overview_panel(status: dict[str, object], monitor: dict[str, object]) -> Panel:
    pairs = [
        ("DB", _state_word(bool(status["database_ready"]), true_label="정상", false_label="실패")),
        ("인증", _switch_word(bool(status["auth_enabled"]))),
        ("관리자", "필요" if status["bootstrap_required"] else "완료"),
        ("공간", str(status["workspace_name"])),
        ("멤버 수", _count_word(status["member_count"], suffix="명")),
        ("활성 세션", _count_word(monitor["active_session_count"], suffix="건", zero_label="대기")),
    ]
    body = Group(
        _render_pair_grid(pairs),
        Text(f"DB 대상: {status['database_target']} ({status['database_backend']})", style="dim"),
    )
    return Panel(body, title="개요", border_style="bright_blue")


def _render_doctor_panel(doctor: dict[str, object]) -> Panel:
    pairs = [
        ("호스트", str(doctor["host_address"])),
        ("포트", str(doctor["port"])),
        ("연결", _state_word(bool(doctor["tcp_open"]), true_label="정상", false_label="실패")),
        ("헬스", _state_word(bool(doctor["health_ok"]), true_label="정상", false_label="실패")),
        ("준비 API", _optional_state_word(doctor["readiness_available"], false_label="실패")),
        ("워밍업", _optional_state_word(doctor["warming"], true_label="진행", false_label="없음")),
        ("서버 준비", _optional_state_word(doctor["backend_ready"], false_label="대기")),
        ("STT 준비", _optional_state_word(doctor["stt_ready"], false_label="대기")),
    ]
    issue_lines = doctor["issues"] or ["경고 없음"]
    issue_text = Text()
    for index, item in enumerate(issue_lines):
        if index > 0:
            issue_text.append("\n")
        style = "yellow" if item != "경고 없음" else "green"
        issue_text.append(f"- {item}", style=style)
    body = Group(
        _render_pair_grid(pairs),
        Text(""),
        _render_doctor_checks_table(doctor["checks"]),
        Text(""),
        issue_text,
    )
    return Panel(body, title="운영 진단", border_style="green")


def _render_settings_summary_panel(payload: dict[str, object]) -> Panel:
    pairs = [
        ("프로필", str(payload.get("active_profile") or "미사용")),
        ("포트", str(payload["server_port"])),
        ("인증", "켜짐" if str(payload["auth_enabled"]).lower() == "true" else "꺼짐"),
        ("STT", _shorten(str(payload["stt_backend"]), 18)),
        ("장치", str(payload["stt_device"])),
        ("연산", str(payload["stt_compute_type"])),
        ("화자 분리", _shorten(str(payload["speaker_diarizer_backend"]), 18)),
        ("정제", _shorten(str(payload["report_refiner_backend"]), 18)),
    ]
    profiles = _list_settings_profiles()
    body = Group(
        _render_pair_grid(pairs),
        Text(f"저장된 프로필: {_count_word(len(profiles), suffix='개', zero_label='없음')}", style="dim"),
        Text(f".env: {payload['env_path']}", style="dim"),
    )
    return Panel(body, title="설정 요약", border_style="cyan")


def _render_doctor_checks_table(checks: list[dict[str, str]]) -> Table:
    table = Table(expand=True, box=None, show_header=True, header_style="bold")
    table.add_column("체크", width=14)
    table.add_column("상태", width=8)
    table.add_column("상세", ratio=1, overflow="fold")
    for item in checks:
        table.add_row(
            item["label"],
            _doctor_status_text(item["status"]),
            _shorten(item["detail"], 56),
        )
    return table


def _render_audio_monitor_panel(audio_pipeline: dict[str, object], readiness: dict[str, object]) -> Panel:
    pairs = [
        ("확정", _count_word(audio_pipeline.get("recent_final_count"), suffix="건")),
        ("발화", _count_word(audio_pipeline.get("recent_utterance_count"), suffix="건")),
        ("이벤트", _count_word(audio_pipeline.get("recent_event_count"), suffix="건")),
        ("평균 지연", _format_optional_number(audio_pipeline.get("average_queue_delay_ms"), suffix="ms")),
        ("최대 지연", _format_optional_number(audio_pipeline.get("max_queue_delay_ms"), suffix="ms")),
        ("지연 확정", _count_word(audio_pipeline.get("late_final_count"), suffix="건")),
        ("압박", _count_word(audio_pipeline.get("backpressure_count"), suffix="건")),
        ("오류", _count_word(audio_pipeline.get("error_count"), suffix="건")),
    ]
    activity_summary = _build_audio_activity_summary(audio_pipeline)
    body = Group(
        Text(activity_summary["message"], style=activity_summary["style"]),
        _render_pair_grid(pairs),
        Text(
            "최근 오류: "
            + _shorten(str(audio_pipeline.get("last_error_message") or "없음"), 64),
            style="dim",
        ),
        Text(
            "런타임: "
            + f"서버 {_optional_state_word(readiness.get('backend_ready'), false_label='대기')} / "
            + f"워밍업 {_optional_state_word(readiness.get('warming'), true_label='진행', false_label='없음')} / "
            + f"STT {_optional_state_word(readiness.get('stt_ready'), false_label='대기')}",
            style="dim",
        ),
    )
    return Panel(body, title="오디오 파이프라인 모니터", border_style="magenta")


def _render_members_panel(
    rows: list[dict[str, str | None]],
    *,
    title: str,
    compact: bool,
) -> Panel:
    table = Table(expand=True, box=None, show_header=True, header_style="bold")
    table.add_column("역할", width=10)
    table.add_column("이름", width=12)
    table.add_column("이메일", min_width=18)
    if not compact:
        table.add_column("직급", width=12)
        table.add_column("부서", width=12)
    table.add_column("상태", width=10)

    if not rows:
        table.add_row("-", "등록된 멤버가 없습니다.", "-", *([] if compact else ["-", "-"]), "-")
    else:
        for row in rows:
            cells = [
                str(row["workspace_role"] or "-"),
                str(row["display_name"] or "-"),
                str(row["login_id"] or "-"),
            ]
            if not compact:
                cells.extend(
                    [
                        str(row["job_title"] or "-"),
                        str(row["department"] or "-"),
                    ]
                )
            cells.append(str(row["status"] or "-"))
            table.add_row(*cells)
    return Panel(table, title=title, border_style="yellow")


def _render_status_panel(status: dict[str, object]) -> Panel:
    pairs = [
        ("DB", _state_word(bool(status["database_ready"]), true_label="정상", false_label="실패")),
        ("인증", _switch_word(bool(status["auth_enabled"]))),
        ("사용자 수", _count_word(status["user_count"], suffix="명")),
        ("공간", str(status["workspace_name"])),
        ("멤버 수", _count_word(status["member_count"], suffix="명")),
        ("관리자", "필요" if status["bootstrap_required"] else "완료"),
    ]
    body = Group(
        _render_pair_grid(pairs),
        Text(f"DB 대상: {status['database_target']} ({status['database_backend']})", style="dim"),
    )
    return Panel(body, title=f"{CLI_TITLE} · 서버 상태", border_style="cyan")


def _render_next_steps_panel(status: dict[str, object]) -> Panel:
    lines = []
    if status["bootstrap_required"]:
        lines.append('powershell -ExecutionPolicy Bypass -File .\\scripts\\server-admin.ps1 bootstrap-admin --login-id owner --display-name "관리자"')
    else:
        lines.append("powershell -ExecutionPolicy Bypass -File .\\scripts\\server-admin.ps1 dashboard")
        lines.append("powershell -ExecutionPolicy Bypass -File .\\scripts\\server-admin.ps1 list-members")
    if not status["auth_enabled"]:
        lines.append(".env에서 AUTH_ENABLED=true 설정")
    return _render_hint_panel("다음 단계", lines)


def _render_doctor_hint_panel(doctor: dict[str, object]) -> Panel:
    lines = []
    if doctor["tcp_open"]:
        lines.append("서버 포트는 열려 있습니다.")
    else:
        lines.append("dev-server.ps1 또는 dev-stack.ps1로 서버를 먼저 실행하세요.")
    if not doctor["health_ok"]:
        lines.append("uvicorn 로그와 /health 응답을 확인하세요.")
    if doctor["readiness_available"] and doctor["stt_ready"] is False:
        lines.append("STT preload 또는 런타임 워밍업 상태를 확인하세요.")
    if not lines:
        lines.append("문제 없음. dashboard에서 모니터 수치를 계속 확인하세요.")
    return _render_hint_panel("진단 가이드", lines)


def _render_result_panel(title: str, payload: dict[str, object]) -> Panel:
    pairs = [
        ("로그인 아이디", str(payload.get("login_id") or "-")),
        ("이름", str(payload.get("display_name") or "-")),
        ("워크스페이스", str(payload.get("workspace_name") or "-")),
        ("역할", str(payload.get("workspace_role") or "-")),
        ("직급", str(payload.get("job_title") or "-")),
        ("부서", str(payload.get("department") or "-")),
    ]
    return Panel(_render_pair_grid(pairs), title=title, border_style="green")


def _render_hint_panel(title: str, lines: list[str]) -> Panel:
    text = Text()
    for index, line in enumerate(lines):
        if index > 0:
            text.append("\n")
        text.append(f"- {line}")
    return Panel(text, title=title, border_style="blue")


def _render_pair_grid(pairs: list[tuple[str, str]]) -> Table:
    grid = Table.grid(expand=True, padding=(0, 1))
    grid.add_column(style="bold cyan", width=10, no_wrap=True)
    grid.add_column(style="white", ratio=3, overflow="fold")
    grid.add_column(style="bold cyan", width=10, no_wrap=True)
    grid.add_column(style="white", ratio=3, overflow="fold")

    normalized_pairs = list(pairs)
    if len(normalized_pairs) % 2 == 1:
        normalized_pairs.append(("", ""))

    for index in range(0, len(normalized_pairs), 2):
        left_label, left_value = normalized_pairs[index]
        right_label, right_value = normalized_pairs[index + 1]
        grid.add_row(left_label, left_value, right_label, right_value)
    return grid


def _render_actions_panel(logs_payload: dict[str, object]) -> Panel:
    return Panel(
        Text.from_markup(
            "[bold]빠른 작업[/bold]\n"
            "1 관리자 생성   2 멤버 추가   3 역할 변경   4 멤버 전체 보기\n"
            "5 doctor   6 live logs   7 settings   8 profiles   R 새로고침   Q 종료\n"
            f"[dim]로그 파일: {logs_payload['log_file_path']}[/dim]"
        ),
        border_style="blue",
    )


def _render_settings_panel(payload: dict[str, object]) -> Panel:
    pairs = [
        ("프로필", str(payload.get("active_profile") or "미사용")),
        ("호스트", str(payload["server_host"])),
        ("포트", str(payload["server_port"])),
        ("인증", "켜짐" if str(payload["auth_enabled"]).lower() == "true" else "꺼짐"),
        ("로그", str(payload["log_level"])),
        ("STT", _shorten(str(payload["stt_backend"]), 22)),
        ("시스템 STT", _shorten(str(payload["stt_system_backend"] or "-"), 22)),
        ("장치", str(payload["stt_device"])),
        ("연산", str(payload["stt_compute_type"])),
        ("화자 분리", str(payload["speaker_diarizer_backend"])),
        ("분리 장치", str(payload["speaker_diarizer_device"])),
        ("LLM URL", _shorten(str(payload["llm_base_url"] or "-"), 26)),
        ("회의록 정제", str(payload["report_refiner_backend"])),
    ]
    body = Group(
        _render_pair_grid(pairs),
        Text(f".env 경로: {payload['env_path']}", style="dim"),
        Text(
            "갱신 키: " + ", ".join(payload.get("updated_keys", [])) if payload.get("updated_keys") else "갱신 키: 없음",
            style="dim",
        ),
    )
    return Panel(body, title="설정 적용 결과", border_style="cyan")


def _render_profiles_panel(rows: list[dict[str, object]], *, title: str) -> Panel:
    if not rows:
        return Panel.fit(
            Text("저장된 프로필이 없습니다. settings 또는 profiles save로 복구 지점을 만드세요.", style="dim"),
            title=title,
            border_style="bright_blue",
        )

    table = Table(expand=False, box=None, show_header=True, header_style="bold")
    table.add_column("프로필", width=18)
    table.add_column("상태", width=8)
    table.add_column("포트", width=8)
    table.add_column("STT", width=18)
    table.add_column("장치", width=10)
    table.add_column("메모", ratio=1, overflow="fold")

    for row in rows:
        table.add_row(
            str(row.get("name") or "-"),
            "사용 중" if bool(row.get("is_active")) else "보관",
            str(row.get("server_port") or "-"),
            _shorten(str(row.get("stt_backend") or "-"), 18),
            str(row.get("stt_device") or "-"),
            str(row.get("note") or "-"),
        )
    return Panel.fit(table, title=title, border_style="bright_blue")


def _render_logs_panel(
    payload: dict[str, object],
    *,
    follow: bool = False,
    interval: float | None = None,
) -> Panel:
    lines = payload["lines"]
    body = Text()
    if lines:
        for index, line in enumerate(lines):
            if index > 0:
                body.append("\n")
            body.append(str(line))
    else:
        body.append("아직 기록된 로그가 없습니다.", style="dim")

    subtitle = f"최근 {payload['line_count']}줄 / 파일: {payload['log_file_path']}"
    if follow and interval is not None:
        subtitle = f"{subtitle} / follow {interval:.1f}s"
    return Panel(body, title="live logs", subtitle=subtitle, border_style="bright_blue")


def _render_status_banner(status: dict[str, object], doctor: dict[str, object]) -> Panel:
    title = "현재 상태 · 운영 준비 완료"
    style = "green"
    lines: list[str] = []

    if not doctor["tcp_open"]:
        title = "현재 상태 · 서버 미실행"
        style = "red"
        lines.append(f"포트 {doctor['port']}이 열려 있지 않습니다.")
    elif not doctor["health_ok"]:
        title = "현재 상태 · 헬스 체크 실패"
        style = "red"
        lines.append("/health 응답을 받지 못했습니다.")
    elif doctor["readiness_available"] and (
        doctor["backend_ready"] is False or doctor["stt_ready"] is False
    ):
        title = "현재 상태 · 런타임 준비 중"
        style = "yellow"
        lines.append("서버 또는 STT가 아직 준비 중입니다.")

    if status["bootstrap_required"]:
        lines.append("초기 관리자 계정 생성이 필요합니다.")
        if style == "green":
            style = "yellow"
            title = "현재 상태 · 초기 설정 필요"

    if not status["auth_enabled"]:
        lines.append("인증이 꺼져 있어 현재는 개발 모드로 동작합니다.")

    if not lines:
        lines.append("서버, 인증, 기본 운영 상태가 정상으로 보입니다.")

    body = Text()
    for index, line in enumerate(lines):
        if index > 0:
            body.append("\n")
        body.append(f"- {line}")
    return Panel(body, title=title, border_style=style)


def _build_audio_activity_summary(audio_pipeline: dict[str, object]) -> dict[str, str]:
    error_count = int(audio_pipeline.get("error_count") or 0)
    backpressure_count = int(audio_pipeline.get("backpressure_count") or 0)
    late_final_count = int(audio_pipeline.get("late_final_count") or 0)
    final_count = int(audio_pipeline.get("recent_final_count") or 0)
    utterance_count = int(audio_pipeline.get("recent_utterance_count") or 0)
    event_count = int(audio_pipeline.get("recent_event_count") or 0)

    if error_count > 0:
        return {"message": "현재 상태: 오류 감지", "style": "bold red"}
    if backpressure_count > 0 or late_final_count > 0:
        return {"message": "현재 상태: 지연 경고", "style": "bold yellow"}
    if final_count == 0 and utterance_count == 0 and event_count == 0:
        return {"message": "현재 상태: 최근 처리 없음", "style": "dim cyan"}
    return {"message": "현재 상태: 정상 수집 중", "style": "green"}


def _dashboard_bootstrap_admin(console: Console) -> None:
    payload = build_status_payload()
    if not payload["bootstrap_required"]:
        _pause(console, "이미 사용자가 등록되어 있습니다. add-member를 사용하세요.")
        return

    login_id = _prompt_required("관리자 로그인 아이디")
    display_name = _prompt_required("관리자 이름")
    password = getpass.getpass("관리자 비밀번호: ")
    job_title = _prompt_optional("직급")
    department = _prompt_optional("부서")

    try:
        user = get_auth_service().provision_initial_admin(
            login_id=login_id,
            password=password,
            display_name=display_name,
            job_title=job_title,
            department=department,
        )
    except (BootstrapConflictError, ValueError) as error:
        _pause(console, f"실패: {error}")
        return

    _pause(console, f"초기 관리자 생성 완료: {user.login_id} ({user.workspace_role or user.role})")


def _dashboard_add_member(console: Console) -> None:
    login_id = _prompt_required("멤버 로그인 아이디")
    display_name = _prompt_required("멤버 이름")
    role = _prompt_role(default="member")
    password = getpass.getpass("멤버 비밀번호: ")
    job_title = _prompt_optional("직급")
    department = _prompt_optional("부서")

    try:
        user = get_auth_service().create_workspace_user(
            login_id=login_id,
            password=password,
            display_name=display_name,
            job_title=job_title,
            department=department,
            role=role,
        )
    except ValueError as error:
        _pause(console, f"실패: {error}")
        return

    _pause(console, f"멤버 추가 완료: {user.login_id} ({user.workspace_role or user.role})")


def _dashboard_change_member_role(console: Console) -> None:
    login_id = _prompt_required("대상 로그인 아이디")
    role = _prompt_role(default="member")

    try:
        user = get_auth_service().change_workspace_member_role(login_id=login_id, role=role)
    except (UserNotFoundError, ValueError) as error:
        _pause(console, f"실패: {error}")
        return

    _pause(console, f"역할 변경 완료: {user.login_id} -> {user.workspace_role or user.role}")


def _dashboard_show_all_members(console: Console) -> None:
    members = [_member_payload(member) for member in get_auth_service().list_workspace_members()]
    console.clear()
    console.print(_render_members_panel(members, title="워크스페이스 멤버 전체 목록", compact=False))
    _pause(console)


def _dashboard_show_doctor(console: Console, *, host_address: str, port: int) -> None:
    payload = build_doctor_payload(host_address=host_address, port=port)
    console.clear()
    console.print(_render_doctor_panel(payload))
    console.print()
    console.print(_render_doctor_hint_panel(payload))
    _pause(console)


def _dashboard_show_logs(console: Console, *, lines: int) -> None:
    while True:
        payload = build_logs_payload(limit=lines)
        console.clear()
        console.print(_render_logs_panel(payload))
        console.print()
        action = input("선택 [R 새로고침 / F follow / Q 종료]: ").strip().lower()
        if action in {"", "r"}:
            continue
        if action == "f":
            try:
                while True:
                    payload = build_logs_payload(limit=lines)
                    console.clear()
                    console.print(_render_logs_panel(payload, follow=True, interval=1.0))
                    time.sleep(1.0)
            except KeyboardInterrupt:
                continue
        if action == "q":
            return
        _pause(console, f"지원하지 않는 선택입니다: {action}")


def _dashboard_settings(console: Console) -> None:
    updates = _collect_settings_wizard(console)
    if not updates:
        _pause(console, "변경할 설정이 없습니다.")
        return

    written = _write_env_values(ENV_FILE_PATH, updates)
    _apply_env_overrides(updates)
    payload = build_settings_payload()
    payload["updated_keys"] = written
    console.clear()
    console.print(_render_settings_panel(payload))
    if _prompt_bool("이 설정을 프로필로 저장할까요?", False):
        profile_name = _prompt_required("프로필 이름")
        profile = _save_settings_profile(profile_name, note="dashboard settings 저장")
        console.print()
        console.print(_render_profiles_panel([profile], title="프로필 저장 완료"))
    _pause(console, "설정을 저장했습니다. 서버를 다시 시작하면 적용됩니다.")


def _dashboard_profiles(console: Console) -> None:
    while True:
        profiles = _list_settings_profiles()
        console.clear()
        console.print(_render_profiles_panel(profiles, title="설정 프로필"))
        console.print()
        action = input("선택 [S 저장 / A 적용 / D 삭제 / R 새로고침 / Q 종료]: ").strip().lower()
        if action in {"", "r"}:
            continue
        if action == "s":
            name = _prompt_required("프로필 이름")
            note = _prompt_optional("설명 메모")
            profile = _save_settings_profile(name, note=note)
            _pause(console, f"프로필 저장 완료: {profile['name']}")
            continue
        if action == "a":
            name = _prompt_required("적용할 프로필 이름")
            try:
                profile = _apply_settings_profile(name)
            except ValueError as error:
                _pause(console, str(error))
                continue
            _pause(console, f"프로필 적용 완료: {profile['name']} (서버 재시작 필요)")
            continue
        if action == "d":
            name = _prompt_required("삭제할 프로필 이름")
            try:
                _delete_settings_profile(name)
            except ValueError as error:
                _pause(console, str(error))
                continue
            _pause(console, f"프로필 삭제 완료: {name}")
            continue
        if action == "q":
            return
        _pause(console, f"지원하지 않는 선택입니다: {action}")


def _member_payload(member) -> dict[str, str | None]:
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


def _build_console() -> Console:
    return Console(soft_wrap=True)


def _print_error(message: str) -> None:
    print(f"[오류] {message}", file=sys.stderr)


def _bool_to_korean(value: object) -> str:
    return "예" if bool(value) else "아니오"


def _bool_to_env_value(value: object) -> str:
    return "true" if bool(value) else "false"


def _state_word(
    value: bool,
    *,
    true_label: str = "정상",
    false_label: str = "실패",
) -> str:
    return true_label if value else false_label


def _optional_state_word(
    value: object,
    *,
    true_label: str = "정상",
    false_label: str = "실패",
    none_label: str = "미수집",
) -> str:
    if value is None:
        return none_label
    return true_label if bool(value) else false_label


def _doctor_check(label: str, status: str, detail: str) -> dict[str, str]:
    return {"label": label, "status": status, "detail": detail}


def _doctor_status_text(status: str) -> str:
    mapping = {
        "ok": "정상",
        "warn": "경고",
        "fail": "실패",
        "pending": "미수집",
    }
    return mapping.get(status, status)


def _switch_word(value: bool) -> str:
    return "켜짐" if value else "꺼짐"


def _count_word(value: object, *, suffix: str = "건", zero_label: str | None = None) -> str:
    numeric = int(value or 0)
    if numeric == 0 and zero_label is not None:
        return zero_label
    return f"{numeric}{suffix}"


def _format_optional_bool(value: object) -> str:
    if value is None:
        return "미수집"
    return _state_word(bool(value), true_label="정상", false_label="대기")


def _format_optional_number(value: object, *, suffix: str = "") -> str:
    if value is None:
        return "미수집"
    return f"{value}{suffix}"


def _shorten(text: str, width: int) -> str:
    if len(text) <= width:
        return text
    return text[: width - 3] + "..."


def _prompt_required(label: str) -> str:
    while True:
        value = input(f"{label}: ").strip()
        if value:
            return value
        print("값을 비워둘 수 없습니다.")


def _prompt_optional(label: str) -> str | None:
    value = input(f"{label} (선택): ").strip()
    return value or None


def _prompt_role(default: str) -> str:
    while True:
        raw = input(f"역할 [{'/'.join(ROLE_CHOICES)}] (기본값: {default}): ").strip().lower()
        value = raw or default
        if value in ROLE_CHOICES:
            return value
        print(f"지원하는 역할만 입력해 주세요: {', '.join(ROLE_CHOICES)}")


def _prompt_choice(label: str, choices: tuple[str, ...], default: str) -> str:
    normalized = {choice.lower(): choice for choice in choices}
    while True:
        raw = input(f"{label} [{'/'.join(choices)}] (기본값: {default}): ").strip()
        if not raw:
            return default
        value = normalized.get(raw.lower())
        if value is not None:
            return value
        print(f"지원하는 값만 입력해 주세요: {', '.join(choices)}")


def _prompt_int(label: str, default: int) -> int:
    while True:
        raw = input(f"{label} (기본값: {default}): ").strip()
        if not raw:
            return default
        try:
            return int(raw)
        except ValueError:
            print("숫자만 입력해 주세요.")


def _prompt_bool(label: str, default: bool) -> bool:
    default_label = "y" if default else "n"
    while True:
        raw = input(f"{label} [y/n] (기본값: {default_label}): ").strip().lower()
        if not raw:
            return default
        if raw in {"y", "yes"}:
            return True
        if raw in {"n", "no"}:
            return False
        print("y 또는 n만 입력해 주세요.")


def _pause(console: Console, message: str | None = None) -> None:
    if message:
        console.print(f"[yellow]{message}[/yellow]")
    input("계속하려면 Enter를 누르세요...")


def _probe_tcp_port(host_address: str, port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.settimeout(1.0)
        return sock.connect_ex((host_address, port)) == 0


def _tail_log_lines(path: Path, *, limit: int) -> list[str]:
    if not path.exists():
        return []

    with path.open("r", encoding="utf-8", errors="replace") as handle:
        return [line.rstrip("\r\n") for line in deque(handle, maxlen=max(1, limit))]


def _resolve_project_path(raw_path: str) -> Path:
    candidate = Path(raw_path)
    if candidate.is_absolute():
        return candidate
    return PROJECT_ROOT / candidate


def _fetch_json(url: str) -> tuple[dict[str, object] | None, str | None]:
    try:
        with urllib.request.urlopen(url, timeout=1.5) as response:
            if response.status != 200:
                return None, f"HTTP {response.status}"
            payload = json.loads(response.read().decode("utf-8"))
            if isinstance(payload, dict):
                return payload, None
            return None, "응답 형식이 dict가 아닙니다."
    except urllib.error.URLError as error:
        return None, str(error.reason)
    except Exception as error:  # noqa: BLE001
        return None, str(error)


def _read_env_values(path: Path) -> dict[str, str]:
    source_path = path if path.exists() else ENV_EXAMPLE_PATH
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


def _write_env_values(path: Path, updates: dict[str, str]) -> list[str]:
    source_path = path if path.exists() else ENV_EXAMPLE_PATH
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


def _has_explicit_settings_args(args: argparse.Namespace) -> bool:
    return any(
        getattr(args, attr) not in (None, "")
        for attr in (
            "preset",
            "server_host",
            "server_port",
            "auth_enabled",
            "log_level",
            "stt_backend",
            "stt_system_backend",
            "stt_device",
            "stt_compute_type",
            "stt_base_url",
            "ryzen_ai_path",
            "speaker_diarizer_backend",
            "speaker_diarizer_device",
            "llm_base_url",
            "report_refiner_backend",
        )
    )


def _build_settings_updates_from_args(args: argparse.Namespace) -> dict[str, str]:
    updates: dict[str, str] = {}
    if args.preset:
        updates.update(SETTINGS_PROFILE_MAP[args.preset])

    direct_values = {
        "SERVER_HOST": args.server_host,
        "SERVER_PORT": str(args.server_port) if args.server_port else None,
        "AUTH_ENABLED": args.auth_enabled,
        "LOG_LEVEL": args.log_level,
        "STT_BACKEND": args.stt_backend,
        "STT_BACKEND_SYSTEM_AUDIO": args.stt_system_backend,
        "STT_DEVICE": args.stt_device,
        "STT_COMPUTE_TYPE": args.stt_compute_type,
        "STT_BASE_URL": args.stt_base_url,
        "RYZEN_AI_INSTALLATION_PATH": args.ryzen_ai_path,
        "SPEAKER_DIARIZER_BACKEND": args.speaker_diarizer_backend,
        "SPEAKER_DIARIZER_DEVICE": args.speaker_diarizer_device,
        "LLM_BASE_URL": args.llm_base_url,
        "REPORT_REFINER_BACKEND": args.report_refiner_backend,
    }

    for key, value in direct_values.items():
        if value not in (None, ""):
            updates[key] = str(value)
    return updates


def _collect_settings_wizard(console: Console) -> dict[str, str]:
    current = build_settings_payload()
    console.clear()
    console.print(
        Panel(
            Text.from_markup(
                "[bold]서버 설정 마법사[/bold]\n"
                "포트, 인증, STT 하드웨어 프리셋, LLM 연결을 한 번에 저장합니다."
            ),
            border_style="cyan",
        )
    )

    preset = _prompt_choice("하드웨어 프리셋", SETTINGS_PRESET_CHOICES, "cpu-local")
    updates = dict(SETTINGS_PROFILE_MAP[preset])
    updates["SERVER_HOST"] = _prompt_optional(f"서버 호스트 (현재: {current['server_host']})") or str(current["server_host"])
    updates["SERVER_PORT"] = str(_prompt_int("서버 포트", int(current["server_port"])))
    updates["AUTH_ENABLED"] = "true" if _prompt_bool("로그인 인증을 강제할까요?", str(current["auth_enabled"]).lower() == "true") else "false"
    updates["LOG_LEVEL"] = _prompt_choice("로그 레벨", ("DEBUG", "INFO", "WARNING", "ERROR"), str(current["log_level"]))

    if preset == "api-relay":
        updates["STT_BASE_URL"] = _prompt_optional(f"외부 STT URL (현재: {current['stt_base_url'] or '미설정'})") or str(current["stt_base_url"] or "")
        updates["LLM_BASE_URL"] = _prompt_optional(f"LLM URL (현재: {current['llm_base_url'] or '미설정'})") or str(current["llm_base_url"] or "")
    elif preset == "amd-npu":
        updates["RYZEN_AI_INSTALLATION_PATH"] = _prompt_optional(
            f"RyzenAI 설치 경로 (현재: {current['ryzen_ai_installation_path'] or '미설정'})"
        ) or str(current["ryzen_ai_installation_path"] or "")
    else:
        keep_llm = _prompt_bool("기존 LLM URL을 유지할까요?", True)
        if not keep_llm:
            updates["LLM_BASE_URL"] = _prompt_optional(f"LLM URL (현재: {current['llm_base_url'] or '미설정'})") or str(current["llm_base_url"] or "")

    diarizer_backend_default = str(current["speaker_diarizer_backend"])
    updates["SPEAKER_DIARIZER_BACKEND"] = _prompt_choice(
        "화자 분리 backend",
        ("unknown_speaker", "pyannote_worker", "pyannote"),
        diarizer_backend_default,
    )
    updates["SPEAKER_DIARIZER_DEVICE"] = _prompt_choice(
        "화자 분리 device",
        ("cpu", "cuda"),
        str(current["speaker_diarizer_device"]),
    )

    return updates


def main() -> int:
    configure_console_encoding()
    parser = build_parser()
    args = parser.parse_args()
    initialize_primary_persistence()

    if args.command == "dashboard":
        return run_dashboard(args)
    if args.command == "doctor":
        return print_doctor(args.output, host_address=args.host_address, port=args.port)
    if args.command == "logs":
        return print_logs(
            args.output,
            lines=args.lines,
            follow=args.follow,
            interval=args.interval,
        )
    if args.command == "status":
        return print_status(args.output)
    if args.command == "bootstrap-admin":
        return bootstrap_admin(args)
    if args.command == "list-members":
        return list_members(args.output)
    if args.command == "add-member":
        return add_member(args)
    if args.command == "change-member-role":
        return change_member_role(args)
    if args.command == "settings":
        return apply_settings(args)
    if args.command == "profiles":
        return manage_profiles(args)

    parser.error("지원하지 않는 명령입니다.")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
