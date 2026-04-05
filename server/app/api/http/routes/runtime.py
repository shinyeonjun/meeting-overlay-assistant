"""런타임 readiness / monitor 라우터."""

from fastapi import APIRouter, Depends, Query

from server.app.api.http.dependencies import (
    get_live_stream_service,
    get_runtime_monitor_service,
    get_session_service,
)
from server.app.api.http.schemas.runtime_monitor import RuntimeMonitorResponse
from server.app.api.http.security import require_authenticated_session
from server.app.core.runtime_readiness import get_runtime_readiness
from server.app.services.observability.runtime.runtime_monitor_service import RuntimeMonitorService


router = APIRouter(tags=["runtime"])


@router.get("/api/v1/runtime/readiness")
def runtime_readiness() -> dict[str, object]:
    """현재 런타임 readiness 상태를 반환한다."""

    return get_runtime_readiness()


@router.get("/api/v1/runtime/monitor", response_model=RuntimeMonitorResponse)
def runtime_monitor(
    session_id: str | None = Query(default=None),
    _: object = Depends(require_authenticated_session),
    runtime_monitor_service: RuntimeMonitorService = Depends(get_runtime_monitor_service),
) -> RuntimeMonitorResponse:
    """라이브 런타임 운영 지표를 반환한다."""

    snapshot = runtime_monitor_service.build_snapshot(session_id=session_id)
    live_stream_snapshot = get_live_stream_service().build_snapshot()
    return RuntimeMonitorResponse(
        generated_at=snapshot["generated_at"],
        active_session_count=get_session_service().count_running_sessions(),
        readiness=get_runtime_readiness(),
        audio_pipeline=snapshot["audio_pipeline"],
        live_stream=live_stream_snapshot,
    )
