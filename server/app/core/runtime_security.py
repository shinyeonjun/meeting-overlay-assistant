"""서버를 어디까지 노출해도 되는지 기동 시점에 판단한다."""

from __future__ import annotations

LOOPBACK_HOSTS = frozenset({"127.0.0.1", "localhost", "::1"})
PRODUCTION_APP_ENVS = frozenset({"production", "prod"})


def is_loopback_host(host: str) -> bool:
    """루프백 주소인지 확인한다."""

    return host.strip().lower() in LOOPBACK_HOSTS


def assert_safe_exposure(*, server_host: str, app_env: str, auth_enabled: bool) -> None:
    """인증 없이 외부에 노출되는 구성이면 기동을 거부한다."""

    if auth_enabled:
        return
    if app_env.strip().lower() in PRODUCTION_APP_ENVS:
        raise RuntimeError("APP_ENV가 production인데 AUTH_ENABLED=false입니다. 인증을 켜고 다시 기동하세요.")
    if not is_loopback_host(server_host):
        raise RuntimeError(
            f"SERVER_HOST={server_host!r}는 루프백이 아닌데 AUTH_ENABLED=false입니다. "
            "인증을 켜거나 SERVER_HOST를 127.0.0.1로 두세요."
        )
