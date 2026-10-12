"""setup_server 대시보드와 명령 결과를 Rich 패널로 그린다."""

from __future__ import annotations

import sys

from rich.columns import Columns
from rich.console import Console, Group
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from server.scripts.admin.setup_support.formatting import (
    _state_word,
    _optional_state_word,
    _doctor_status_text,
    _switch_word,
    _count_word,
    _format_optional_number,
    _shorten,
    _build_audio_activity_summary,
)


CLI_TITLE = "CAPS SERVER SETUP"
DASHBOARD_TITLE = "CAPS 운영 대시보드"


def build_console() -> Console:
    return Console(soft_wrap=True)


def print_error(message: str) -> None:
    print(f"[오류] {message}", file=sys.stderr)


def _render_dashboard_group(payload: dict[str, object], *, profile_count: int) -> Group:
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
            _render_settings_summary_panel(settings_payload, profile_count=profile_count),
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


def _render_settings_summary_panel(payload: dict[str, object], *, profile_count: int) -> Panel:
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
    body = Group(
        _render_pair_grid(pairs),
        Text(f"저장된 프로필: {_count_word(profile_count, suffix='개', zero_label='없음')}", style="dim"),
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
        ("리포트 정제", str(payload["report_refiner_backend"])),
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
