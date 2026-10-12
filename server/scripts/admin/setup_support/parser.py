"""setup_server 하위 명령의 argparse 정의를 모은다."""

from __future__ import annotations

import argparse

from server.scripts.admin.setup_support.config import (
    DEFAULT_LOG_LINES,
    DEFAULT_SERVER_HOST,
    DEFAULT_SERVER_PORT,
    ROLE_CHOICES,
    SETTINGS_PRESET_CHOICES,
)


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
            '  powershell -ExecutionPolicy Bypass -File .\\scripts\\server-admin.ps1 profiles save office-cuda --note "사내 GPU 서버 기본값"\n'
            "  powershell -ExecutionPolicy Bypass -File .\\scripts\\server-admin.ps1 status\n"
            '  powershell -ExecutionPolicy Bypass -File .\\scripts\\server-admin.ps1 bootstrap-admin --login-id owner --display-name "관리자"\n'
            '  powershell -ExecutionPolicy Bypass -File .\\scripts\\server-admin.ps1 add-member --login-id member --display-name "홍길동" --role member\n'
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
    settings_parser.add_argument("--report-refiner-backend", help="리포트 정제 backend")
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
