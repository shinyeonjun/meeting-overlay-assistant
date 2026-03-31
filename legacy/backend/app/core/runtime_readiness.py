"""런타임 준비 상태를 추적한다."""

from __future__ import annotations

from copy import deepcopy
from threading import Lock


_lock = Lock()
_state: dict[str, object] = {
    "backend_ready": False,
    "warming": True,
    "stt_ready": False,
    "stt_preload_enabled": True,
    "preloaded_sources": {},
}


def reset_runtime_readiness(*, stt_preload_enabled: bool) -> None:
    """애플리케이션 시작 시 readiness 상태를 초기화한다."""

    with _lock:
        _state["backend_ready"] = False
        _state["warming"] = True
        _state["stt_ready"] = False
        _state["stt_preload_enabled"] = stt_preload_enabled
        _state["preloaded_sources"] = {}


def mark_source_pending(source: str, *, backend: str, shared_instance: bool) -> None:
    """사전 로드 예정인 source 상태를 등록한다."""

    with _lock:
        sources = _state["preloaded_sources"]
        assert isinstance(sources, dict)
        sources[source] = {
            "backend": backend,
            "shared_instance": shared_instance,
            "ready": False,
            "error": None,
        }


def mark_source_ready(source: str) -> None:
    """source preload 성공을 기록한다."""

    with _lock:
        sources = _state["preloaded_sources"]
        assert isinstance(sources, dict)
        item = sources.setdefault(source, {})
        item["ready"] = True
        item["error"] = None


def mark_source_failed(source: str, error_message: str) -> None:
    """source preload 실패를 기록한다."""

    with _lock:
        sources = _state["preloaded_sources"]
        assert isinstance(sources, dict)
        item = sources.setdefault(source, {})
        item["ready"] = False
        item["error"] = error_message


def finalize_runtime_readiness() -> None:
    """현재 preload 결과를 기반으로 최종 readiness를 계산한다."""

    with _lock:
        sources = _state["preloaded_sources"]
        assert isinstance(sources, dict)
        _state["warming"] = False
        if not _state["stt_preload_enabled"]:
            _state["stt_ready"] = False
        elif not sources:
            _state["stt_ready"] = True
        else:
            _state["stt_ready"] = all(bool(item.get("ready")) for item in sources.values())
        _state["backend_ready"] = True


def get_runtime_readiness() -> dict[str, object]:
    """현재 readiness 스냅샷을 반환한다."""

    with _lock:
        return deepcopy(_state)
