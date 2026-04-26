"""Live stream job policy helper 테스트."""

from __future__ import annotations

from types import SimpleNamespace

from server.app.services.audio.runtime.contexts.helpers.job_policy import (
    is_job_kind_ready,
    next_job_kind,
    preferred_ready_kind,
    ready_job_kinds,
    resolve_job_kind,
    should_prioritize_bootstrap_preview,
)


class _FakeContext(SimpleNamespace):
    def is_job_kind_busy(self, job_kind: str) -> bool:
        return bool(getattr(self, f"{job_kind}_busy", False))


def _build_context(**overrides):
    defaults = {
        "preview_bootstrap_pending": False,
        "has_pending_preview_chunk": False,
        "input_closed": False,
        "supports_preview": True,
        "pending_final_chunk_count": 0,
        "preview_ready_max_pending_finals": 2,
        "has_pending_final_chunks": False,
        "has_pending_chunks": False,
        "preview_busy": False,
        "final_busy": False,
    }
    defaults.update(overrides)
    return _FakeContext(**defaults)


def test_bootstrap_preview를_우선해야하는지_판단한다() -> None:
    context = _build_context(
        preview_bootstrap_pending=True,
        has_pending_preview_chunk=True,
    )

    assert should_prioritize_bootstrap_preview(context) is True


def test_preview는_pending_final이_너무많으면_준비되지_않는다() -> None:
    context = _build_context(
        has_pending_preview_chunk=True,
        has_pending_chunks=True,
        pending_final_chunk_count=4,
        preview_ready_max_pending_finals=2,
    )

    assert is_job_kind_ready(context, "preview") is False


def test_input_closed이면_final을_우선한다() -> None:
    context = _build_context(
        input_closed=True,
        has_pending_final_chunks=True,
        has_pending_chunks=True,
    )

    assert preferred_ready_kind(context) == "final"
    assert next_job_kind(context) == "final"


def test_ready_job_kinds는_preview와_final을_함께_반환할수있다() -> None:
    context = _build_context(
        has_pending_preview_chunk=True,
        has_pending_final_chunks=True,
        has_pending_chunks=True,
        pending_final_chunk_count=1,
    )

    assert ready_job_kinds(context) == ["preview", "final"]


def test_resolve_job_kind는_preferred가_준비되지않으면_대체한다() -> None:
    context = _build_context(
        has_pending_final_chunks=True,
        has_pending_chunks=True,
        supports_preview=False,
    )

    assert resolve_job_kind(context, preferred_kind="preview") == "final"
