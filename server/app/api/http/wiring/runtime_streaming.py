"""?ㅼ떆媛??ㅽ듃由??고???議곕┰湲?"""

from __future__ import annotations

from server.app.services.audio.runtime.services.live_stream_service import LiveStreamService
from server.app.services.observability.runtime.runtime_monitor_service import RuntimeMonitorService


def build_live_stream_service(
    *,
    settings,
    runtime_monitor_service: RuntimeMonitorService | None = None,
) -> LiveStreamService:
    """?ㅼ떆媛??ㅽ듃由??고????쒕퉬?ㅻ? 議곕┰?쒕떎."""

    return LiveStreamService(
        worker_count=settings.live_stream_worker_count,
        pending_chunks_per_stream=settings.live_stream_pending_chunks_per_stream,
        max_running_streams=settings.live_stream_max_running_sessions,
        runtime_monitor_service=runtime_monitor_service,
    )
