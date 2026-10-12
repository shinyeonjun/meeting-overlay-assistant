"""설정 명령의 입력(CLI 인자 또는 대화형 마법사)을 .env 갱신값으로 바꾼다."""

from __future__ import annotations

import argparse

from rich.console import Console
from rich.panel import Panel
from rich.text import Text

from server.scripts.admin.setup_support.config import (
    SETTINGS_PRESET_CHOICES,
    SETTINGS_PROFILE_MAP,
    SetupConfig,
)
from server.scripts.admin.setup_support.payloads import build_settings_payload
from server.scripts.admin.setup_support.prompts import (
    _prompt_bool,
    _prompt_choice,
    _prompt_int,
    _prompt_optional,
)


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


def _collect_settings_wizard(cfg: SetupConfig, console: Console) -> dict[str, str]:
    current = build_settings_payload(cfg)
    console.clear()
    console.print(
        Panel(
            Text.from_markup(
                "[bold]서버 설정 마법사[/bold]\n포트, 인증, STT 하드웨어 프리셋, LLM 연결을 한 번에 저장합니다."
            ),
            border_style="cyan",
        )
    )

    preset = _prompt_choice("하드웨어 프리셋", SETTINGS_PRESET_CHOICES, "cpu-local")
    updates = dict(SETTINGS_PROFILE_MAP[preset])
    updates["SERVER_HOST"] = _prompt_optional(f"서버 호스트 (현재: {current['server_host']})") or str(
        current["server_host"]
    )
    updates["SERVER_PORT"] = str(_prompt_int("서버 포트", int(current["server_port"])))
    updates["AUTH_ENABLED"] = (
        "true" if _prompt_bool("로그인 인증을 강제할까요?", str(current["auth_enabled"]).lower() == "true") else "false"
    )
    updates["LOG_LEVEL"] = _prompt_choice("로그 레벨", ("DEBUG", "INFO", "WARNING", "ERROR"), str(current["log_level"]))

    if preset == "api-relay":
        updates["STT_BASE_URL"] = _prompt_optional(
            f"외부 STT URL (현재: {current['stt_base_url'] or '미설정'})"
        ) or str(current["stt_base_url"] or "")
        updates["LLM_BASE_URL"] = _prompt_optional(f"LLM URL (현재: {current['llm_base_url'] or '미설정'})") or str(
            current["llm_base_url"] or ""
        )
    elif preset == "amd-npu":
        updates["RYZEN_AI_INSTALLATION_PATH"] = _prompt_optional(
            f"RyzenAI 설치 경로 (현재: {current['ryzen_ai_installation_path'] or '미설정'})"
        ) or str(current["ryzen_ai_installation_path"] or "")
    else:
        keep_llm = _prompt_bool("기존 LLM URL을 유지할까요?", True)
        if not keep_llm:
            updates["LLM_BASE_URL"] = _prompt_optional(f"LLM URL (현재: {current['llm_base_url'] or '미설정'})") or str(
                current["llm_base_url"] or ""
            )

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
