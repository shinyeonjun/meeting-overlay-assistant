"""이벤트 라우트 진입점."""

from __future__ import annotations

from fastapi import APIRouter, Depends

from server.app.api.http.routes.events.query import router as event_query_router
from server.app.api.http.routes.events.transition import router as event_transition_router
from server.app.api.http.security import require_authenticated_session


router = APIRouter(
    prefix="/api/v1/sessions/{session_id}/events",
    tags=["events"],
    dependencies=[Depends(require_authenticated_session)],
)

router.include_router(event_transition_router)
router.include_router(event_query_router)
