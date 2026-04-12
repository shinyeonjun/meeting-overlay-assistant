"""HTTP 계층에서 공통 관련 runtime streaming 구성을 담당한다."""
from __future__ import annotations

from server.app.services.audio.runtime.services.live_stream_service import LiveStreamService
from server.app.services.observability.runtime.runtime_monitor_service import RuntimeMonitorService


def build_live_stream_service(
    *,
    settings,
    runtime_monitor_service: RuntimeMonitorService | None = None,
) -> LiveStreamService:
    """공통 흐름에서 build live stream service 로직을 수행한다."""

    return LiveStreamService(
        worker_count=settings.live_stream_worker_count,
        pending_chunks_per_stream=settings.live_stream_pending_chunks_per_stream,
        max_running_streams=settings.live_stream_max_running_sessions,
        runtime_monitor_service=runtime_monitor_service,
    )
