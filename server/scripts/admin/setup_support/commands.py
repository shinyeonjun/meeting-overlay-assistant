"""일회성 CLI 명령(멤버·상태·진단·로그·설정·프로필)의 실행과 출력을 담당한다."""

from __future__ import annotations

import argparse
import getpass
import json
import time
from datetime import datetime

from server.app.api.http.dependencies import get_auth_service
from server.app.contexts.identity import BootstrapConflictError, UserNotFoundError
from server.scripts.admin.setup_support.config import SETTINGS_PROFILE_ENV_KEY, SetupConfig
from server.scripts.admin.setup_support.doctor import build_doctor_payload
from server.scripts.admin.setup_support.envfile import _apply_env_overrides, _write_env_values
from server.scripts.admin.setup_support.payloads import (
    build_logs_payload,
    build_settings_payload,
    build_status_payload,
    member_payload,
)
from server.scripts.admin.setup_support.profiles import (
    _apply_settings_profile,
    _delete_settings_profile,
    _list_settings_profiles,
    _save_settings_profile,
)
from server.scripts.admin.setup_support.render import (
    _render_doctor_hint_panel,
    _render_doctor_panel,
    _render_hint_panel,
    _render_logs_panel,
    _render_members_panel,
    _render_next_steps_panel,
    _render_profiles_panel,
    _render_result_panel,
    _render_settings_panel,
    _render_status_panel,
    build_console,
    print_error,
)
from server.scripts.admin.setup_support.settings_updates import (
    _build_settings_updates_from_args,
    _collect_settings_wizard,
    _has_explicit_settings_args,
)


def bootstrap_admin(cfg: SetupConfig, args: argparse.Namespace) -> int:
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
        print_error(str(error))
        return 1
    except ValueError as error:
        print_error(str(error))
        return 1

    payload = member_payload(user)
    payload["auth_enabled"] = cfg.app_settings.auth_enabled
    if args.output == "json":
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        return 0

    console = build_console()
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
    payload = [member_payload(member) for member in members]
    if output_mode == "json":
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        return 0

    console = build_console()
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
        print_error(str(error))
        return 1

    payload = member_payload(user)
    if args.output == "json":
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        return 0

    console = build_console()
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
        print_error(str(error))
        return 1
    except ValueError as error:
        print_error(str(error))
        return 1

    payload = member_payload(user)
    if args.output == "json":
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        return 0

    console = build_console()
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


def print_status(cfg: SetupConfig, output_mode: str) -> int:
    payload = build_status_payload(cfg)
    if output_mode == "json":
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        return 0

    console = build_console()
    console.print(_render_status_panel(payload))
    console.print()
    console.print(_render_next_steps_panel(payload))
    return 0


def print_doctor(
    cfg: SetupConfig,
    output_mode: str,
    *,
    host_address: str,
    port: int,
) -> int:
    payload = build_doctor_payload(cfg, host_address=host_address, port=port)
    if output_mode == "json":
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        return 0

    console = build_console()
    console.print(_render_doctor_panel(payload))
    console.print()
    console.print(_render_doctor_hint_panel(payload))
    return 0


def print_logs(
    cfg: SetupConfig,
    output_mode: str,
    *,
    lines: int,
    follow: bool,
    interval: float,
) -> int:
    payload = build_logs_payload(cfg, limit=lines)
    if output_mode == "json":
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        return 0

    console = build_console()
    if not follow:
        console.print(_render_logs_panel(payload))
        return 0

    try:
        while True:
            payload = build_logs_payload(cfg, limit=lines)
            console.clear()
            console.print(_render_logs_panel(payload, follow=True, interval=interval))
            time.sleep(max(interval, 0.2))
    except KeyboardInterrupt:
        console.print("\n[bold cyan]로그 추적을 종료합니다.[/bold cyan]")
        return 0


def apply_settings(cfg: SetupConfig, args: argparse.Namespace) -> int:
    console = build_console()
    if args.interactive or not _has_explicit_settings_args(args):
        updates = _collect_settings_wizard(cfg, console)
    else:
        updates = _build_settings_updates_from_args(args)

    if not updates:
        if args.output == "json":
            print(json.dumps({"updated": False, "message": "변경할 설정이 없습니다."}, ensure_ascii=False, indent=2))
            return 0
        console.print(_render_hint_panel("설정", ["변경할 설정이 없습니다."]))
        return 0

    written = _write_env_values(cfg, updates)
    _apply_env_overrides(updates)
    payload = build_settings_payload(cfg)
    payload["updated_keys"] = written
    save_profile_name = getattr(args, "save_profile", None)
    if save_profile_name:
        profile = _save_settings_profile(
            cfg,
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


def manage_profiles(cfg: SetupConfig, args: argparse.Namespace) -> int:
    action = args.action
    console = build_console()

    if action == "list":
        profiles = _list_settings_profiles(cfg)
        if args.output == "json":
            print(json.dumps(profiles, ensure_ascii=False, indent=2))
            return 0
        console.print(_render_profiles_panel(profiles, title="저장된 설정 프로필"))
        return 0

    if not args.name:
        print_error("프로필 이름을 함께 입력해 주세요.")
        return 1

    if action == "save":
        profile = _save_settings_profile(cfg, args.name, note=args.note)
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
            profile = _apply_settings_profile(cfg, args.name)
        except ValueError as error:
            print_error(str(error))
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
            deleted = _delete_settings_profile(cfg, args.name)
        except ValueError as error:
            print_error(str(error))
            return 1
        payload = {"deleted": deleted, "name": args.name}
        if args.output == "json":
            print(json.dumps(payload, ensure_ascii=False, indent=2))
            return 0
        console.print(_render_hint_panel("프로필 삭제", [f"{args.name} 프로필을 삭제했습니다."]))
        return 0

    print_error(f"지원하지 않는 프로필 작업입니다: {action}")
    return 1
