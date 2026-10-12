from __future__ import annotations

import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[3]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from server.app.api.http.dependencies import get_runtime_monitor_service  # noqa: E402,F401
from server.app.api.http.wiring.persistence import initialize_primary_persistence  # noqa: E402
from server.app.core.config import settings  # noqa: E402
from server.scripts.admin.setup_support import commands, dashboard, doctor  # noqa: E402
from server.scripts.admin.setup_support import profiles  # noqa: E402
from server.scripts.admin.setup_support.commands import (  # noqa: E402,F401
    add_member,
    change_member_role,
    list_members,
)
from server.scripts.admin.setup_support.config import (  # noqa: E402
    DEFAULT_SERVER_HOST,
    DEFAULT_SERVER_PORT,
    SetupConfig,
)
from server.scripts.admin.setup_support.parser import build_parser  # noqa: E402
from server.scripts.admin.setup_support.prompts import _prompt_role  # noqa: E402,F401


ENV_FILE_PATH = PROJECT_ROOT / ".env"
ENV_EXAMPLE_PATH = PROJECT_ROOT / ".env.example"
SETTINGS_PROFILE_DIR = PROJECT_ROOT / "server" / "data" / "settings_profiles"


def configure_console_encoding() -> None:
    """직접 실행되는 CLI 경로에서만 콘솔 인코딩을 UTF-8로 맞춘다."""

    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    if hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(encoding="utf-8")


def _config() -> SetupConfig:
    # 모듈 전역을 호출 시점에 읽어야 테스트의 monkeypatch가 하위 모듈까지 닿는다.
    return SetupConfig(
        project_root=PROJECT_ROOT,
        app_settings=settings,
        env_path=ENV_FILE_PATH,
        env_example_path=ENV_EXAMPLE_PATH,
        profile_dir=SETTINGS_PROFILE_DIR,
    )


def build_doctor_payload(
    *,
    host_address: str = DEFAULT_SERVER_HOST,
    port: int = DEFAULT_SERVER_PORT,
) -> dict[str, object]:
    return doctor.build_doctor_payload(_config(), host_address=host_address, port=port)


def bootstrap_admin(args) -> int:
    return commands.bootstrap_admin(_config(), args)


def print_status(output_mode: str) -> int:
    return commands.print_status(_config(), output_mode)


def print_doctor(output_mode: str, *, host_address: str, port: int) -> int:
    return commands.print_doctor(_config(), output_mode, host_address=host_address, port=port)


def print_logs(output_mode: str, *, lines: int, follow: bool, interval: float) -> int:
    return commands.print_logs(_config(), output_mode, lines=lines, follow=follow, interval=interval)


def apply_settings(args) -> int:
    return commands.apply_settings(_config(), args)


def manage_profiles(args) -> int:
    return commands.manage_profiles(_config(), args)


def _save_settings_profile(name: str, *, note: str | None = None) -> dict[str, object]:
    return profiles._save_settings_profile(_config(), name, note=note)


def run_dashboard(args) -> int:
    return dashboard.run_dashboard(_config(), args)


def print_dashboard_snapshot(output_mode: str) -> int:
    return dashboard.print_dashboard_snapshot(_config(), output_mode)


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
