"""HTTP 계층에서 세션 관련 router 구성을 담당한다."""
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
from server.app.api.http.routes.session.management import router as session_management_router
from server.app.api.http.routes.session.overview import router as session_overview_router
from server.app.api.http.routes.session.processing import router as session_processing_router
from server.app.api.http.routes.session.recording import router as session_recording_router
from server.app.api.http.routes.session.transcript import router as session_transcript_router
from server.app.api.http.security import require_authenticated_session

router = APIRouter(
    prefix="/api/v1/sessions",
    tags=["sessions"],
    dependencies=[Depends(require_authenticated_session)],
)
router.include_router(session_lifecycle_router)
router.include_router(session_management_router)
router.include_router(participation_query_router)
router.include_router(participation_resolution_router)
router.include_router(participation_followups_router)
router.include_router(session_overview_router)
router.include_router(session_processing_router)
router.include_router(session_recording_router)
router.include_router(session_transcript_router)
