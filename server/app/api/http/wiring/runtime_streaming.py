"""실시간 스트림 런타임 조립기."""

from __future__ import annotations

from server.app.services.audio.runtime.live_stream_service import LiveStreamService


def build_live_stream_service(*, settings) -> LiveStreamService:
    """실시간 스트림 런타임 서비스를 조립한다."""

    return LiveStreamService(
        worker_count=settings.live_stream_worker_count,
        pending_chunks_per_stream=settings.live_stream_pending_chunks_per_stream,
        max_running_streams=settings.live_stream_max_running_sessions,
    )
