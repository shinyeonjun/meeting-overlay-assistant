"""대화형 운영 대시보드 루프와 그 메뉴 동작을 담당한다."""

from __future__ import annotations

import argparse
import getpass
import json
import time

from rich.console import Console

from server.app.api.http.dependencies import get_auth_service
from server.app.contexts.identity import BootstrapConflictError, UserNotFoundError
from server.scripts.admin.setup_support.config import (
    DEFAULT_LOG_LINES,
    DEFAULT_SERVER_HOST,
    DEFAULT_SERVER_PORT,
    SetupConfig,
)
from server.scripts.admin.setup_support.doctor import build_doctor_payload
from server.scripts.admin.setup_support.envfile import _apply_env_overrides, _write_env_values
from server.scripts.admin.setup_support.payloads import (
    build_logs_payload,
    build_monitor_payload,
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
from server.scripts.admin.setup_support.prompts import (
    _pause,
    _prompt_bool,
    _prompt_optional,
    _prompt_required,
    _prompt_role,
)
from server.scripts.admin.setup_support.render import (
    _render_dashboard_group,
    _render_doctor_hint_panel,
    _render_doctor_panel,
    _render_logs_panel,
    _render_members_panel,
    _render_profiles_panel,
    _render_settings_panel,
    build_console,
)
from server.scripts.admin.setup_support.settings_updates import _collect_settings_wizard


def build_dashboard_payload(
    cfg: SetupConfig,
    *,
    member_limit: int = 6,
    host_address: str = DEFAULT_SERVER_HOST,
    port: int = DEFAULT_SERVER_PORT,
    log_lines: int = DEFAULT_LOG_LINES,
) -> dict[str, object]:
    auth_service = get_auth_service()
    members = auth_service.list_workspace_members()
    return {
        "status": build_status_payload(cfg),
        "monitor": build_monitor_payload(),
        "doctor": build_doctor_payload(cfg, host_address=host_address, port=port),
        "settings": build_settings_payload(cfg),
        "logs": build_logs_payload(cfg, limit=log_lines),
        "member_preview": [member_payload(member) for member in members[:member_limit]],
        "member_total": len(members),
    }


def _render_dashboard(cfg: SetupConfig, payload: dict[str, object]):
    return _render_dashboard_group(payload, profile_count=len(_list_settings_profiles(cfg)))


def run_dashboard(cfg: SetupConfig, args: argparse.Namespace) -> int:
    if args.output == "json":
        payload = build_dashboard_payload(
            cfg,
            host_address=args.host_address,
            port=args.port,
            log_lines=args.log_lines,
        )
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        return 0

    console = build_console()
    if args.once:
        console.print(
            _render_dashboard(
                cfg,
                build_dashboard_payload(
                    cfg,
                    host_address=args.host_address,
                    port=args.port,
                    log_lines=args.log_lines,
                ),
            )
        )
        return 0

    while True:
        payload = build_dashboard_payload(
            cfg,
            host_address=args.host_address,
            port=args.port,
            log_lines=args.log_lines,
        )
        console.clear()
        console.print(_render_dashboard(cfg, payload))
        console.print()
        action = (
            input(
                "선택 [R 새로고침 / 1 관리자 생성 / 2 멤버 추가 / 3 역할 변경 / 4 멤버 전체 보기 / 5 doctor / 6 live logs / 7 settings / 8 profiles / Q 종료]: "
            )
            .strip()
            .lower()
        )

        if action in {"", "r"}:
            continue
        if action == "1":
            _dashboard_bootstrap_admin(cfg, console)
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
            _dashboard_show_doctor(cfg, console, host_address=args.host_address, port=args.port)
            continue
        if action == "6":
            _dashboard_show_logs(cfg, console, lines=args.log_lines)
            continue
        if action == "7":
            _dashboard_settings(cfg, console)
            continue
        if action == "8":
            _dashboard_profiles(cfg, console)
            continue
        if action == "q":
            console.print("[bold cyan]대시보드를 종료합니다.[/bold cyan]")
            return 0

        _pause(console, f"알 수 없는 선택입니다: {action}")


def print_dashboard_snapshot(cfg: SetupConfig, output_mode: str) -> int:
    payload = build_dashboard_payload(cfg)
    if output_mode == "json":
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        return 0

    build_console().print(_render_dashboard(cfg, payload))
    return 0


def _dashboard_bootstrap_admin(cfg: SetupConfig, console: Console) -> None:
    payload = build_status_payload(cfg)
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
    members = [member_payload(member) for member in get_auth_service().list_workspace_members()]
    console.clear()
    console.print(_render_members_panel(members, title="워크스페이스 멤버 전체 목록", compact=False))
    _pause(console)


def _dashboard_show_doctor(cfg: SetupConfig, console: Console, *, host_address: str, port: int) -> None:
    payload = build_doctor_payload(cfg, host_address=host_address, port=port)
    console.clear()
    console.print(_render_doctor_panel(payload))
    console.print()
    console.print(_render_doctor_hint_panel(payload))
    _pause(console)


def _dashboard_show_logs(cfg: SetupConfig, console: Console, *, lines: int) -> None:
    while True:
        payload = build_logs_payload(cfg, limit=lines)
        console.clear()
        console.print(_render_logs_panel(payload))
        console.print()
        action = input("선택 [R 새로고침 / F follow / Q 종료]: ").strip().lower()
        if action in {"", "r"}:
            continue
        if action == "f":
            try:
                while True:
                    payload = build_logs_payload(cfg, limit=lines)
                    console.clear()
                    console.print(_render_logs_panel(payload, follow=True, interval=1.0))
                    time.sleep(1.0)
            except KeyboardInterrupt:
                continue
        if action == "q":
            return
        _pause(console, f"지원하지 않는 선택입니다: {action}")


def _dashboard_settings(cfg: SetupConfig, console: Console) -> None:
    updates = _collect_settings_wizard(cfg, console)
    if not updates:
        _pause(console, "변경할 설정이 없습니다.")
        return

    written = _write_env_values(cfg, updates)
    _apply_env_overrides(updates)
    payload = build_settings_payload(cfg)
    payload["updated_keys"] = written
    console.clear()
    console.print(_render_settings_panel(payload))
    if _prompt_bool("이 설정을 프로필로 저장할까요?", False):
        profile_name = _prompt_required("프로필 이름")
        profile = _save_settings_profile(cfg, profile_name, note="dashboard settings 저장")
        console.print()
        console.print(_render_profiles_panel([profile], title="프로필 저장 완료"))
    _pause(console, "설정을 저장했습니다. 서버를 다시 시작하면 적용됩니다.")


def _dashboard_profiles(cfg: SetupConfig, console: Console) -> None:
    while True:
        profiles = _list_settings_profiles(cfg)
        console.clear()
        console.print(_render_profiles_panel(profiles, title="설정 프로필"))
        console.print()
        action = input("선택 [S 저장 / A 적용 / D 삭제 / R 새로고침 / Q 종료]: ").strip().lower()
        if action in {"", "r"}:
            continue
        if action == "s":
            name = _prompt_required("프로필 이름")
            note = _prompt_optional("설명 메모")
            profile = _save_settings_profile(cfg, name, note=note)
            _pause(console, f"프로필 저장 완료: {profile['name']}")
            continue
        if action == "a":
            name = _prompt_required("적용할 프로필 이름")
            try:
                profile = _apply_settings_profile(cfg, name)
            except ValueError as error:
                _pause(console, str(error))
                continue
            _pause(console, f"프로필 적용 완료: {profile['name']} (서버 재시작 필요)")
            continue
        if action == "d":
            name = _prompt_required("삭제할 프로필 이름")
            try:
                _delete_settings_profile(cfg, name)
            except ValueError as error:
                _pause(console, str(error))
                continue
            _pause(console, f"프로필 삭제 완료: {name}")
            continue
        if action == "q":
            return
        _pause(console, f"지원하지 않는 선택입니다: {action}")
