"""setup_server 대화형 입력(프롬프트)과 일시 정지 helper."""

from __future__ import annotations

from rich.console import Console

from server.scripts.admin.setup_support.config import ROLE_CHOICES


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
