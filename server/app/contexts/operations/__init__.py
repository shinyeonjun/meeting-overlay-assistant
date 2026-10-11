"""operations 바운디드 컨텍스트의 공개 API.

다른 컨텍스트와 바깥 계층은 이 패키지만 import한다.
"""

from __future__ import annotations

from importlib import import_module
from typing import TYPE_CHECKING, Any


_LAZY_NAMES = {
    "RuntimeMonitorService": "server.app.contexts.operations.application.observability.runtime.runtime_monitor_service",
}

__all__ = [
    "RuntimeMonitorService",
]


_LAZY_MODULES: dict[str, str] = {}


def __getattr__(name: str) -> Any:
    if name in _LAZY_MODULES:
        return import_module(_LAZY_MODULES[name])
    if name in _LAZY_NAMES:
        return getattr(import_module(_LAZY_NAMES[name]), name)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
