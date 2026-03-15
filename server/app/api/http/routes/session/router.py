"""세션 라우트 진입점."""

from fastapi import APIRouter, Depends

from server.app.api.http.routes.participation.followups import (
    router as participation_followups_router,
)
from server.app.api.http.routes.participation.query import (
    router as participation_query_router,
)
from server.app.api.http.routes.participation.resolution import (
    router as participation_resolution_router,
)
from server.app.api.http.routes.session.lifecycle import router as session_lifecycle_router
from server.app.api.http.routes.session.overview import router as session_overview_router
from server.app.api.http.security import require_authenticated_session

router = APIRouter(
    prefix="/api/v1/sessions",
    tags=["sessions"],
    dependencies=[Depends(require_authenticated_session)],
)
router.include_router(session_lifecycle_router)
router.include_router(participation_query_router)
router.include_router(participation_resolution_router)
router.include_router(participation_followups_router)
router.include_router(session_overview_router)
