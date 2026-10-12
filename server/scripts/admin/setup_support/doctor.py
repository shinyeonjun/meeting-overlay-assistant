"""서버 연결과 설정 상태를 진단하는 doctor payload를 만든다."""

from __future__ import annotations

import json
import socket
import urllib.error
import urllib.request
from pathlib import Path

from server.scripts.admin.setup_support.config import (
    DEFAULT_SERVER_HOST,
    DEFAULT_SERVER_PORT,
    SetupConfig,
)
from server.scripts.admin.setup_support.formatting import _doctor_check
from server.scripts.admin.setup_support.payloads import build_settings_payload


def build_doctor_payload(
    cfg: SetupConfig,
    *,
    host_address: str = DEFAULT_SERVER_HOST,
    port: int = DEFAULT_SERVER_PORT,
) -> dict[str, object]:
    settings_payload = build_settings_payload(cfg)
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
    env_source = env_path if env_path.exists() else cfg.env_example_path
    checks.append(
        _doctor_check(
            "환경 파일",
            "ok" if env_path.exists() else "warn",
            str(env_source),
        )
    )

    log_file_path = cfg.app_settings.log_file_path
    log_parent = log_file_path.parent
    log_status = "ok" if log_parent.exists() else "warn"
    log_detail = str(log_file_path)
    checks.append(_doctor_check("로그 경로", log_status, log_detail))
    if log_status != "ok":
        issues.append(f"로그 디렉터리가 없습니다: {log_parent}")

    worker_script_raw = str(settings_payload["speaker_diarizer_worker_script_path"] or "").strip()
    if worker_script_raw:
        worker_script_path = _resolve_project_path(cfg, worker_script_raw)
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


def _probe_tcp_port(host_address: str, port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.settimeout(1.0)
        return sock.connect_ex((host_address, port)) == 0


def _resolve_project_path(cfg: SetupConfig, raw_path: str) -> Path:
    candidate = Path(raw_path)
    if candidate.is_absolute():
        return candidate
    return cfg.project_root / candidate


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
