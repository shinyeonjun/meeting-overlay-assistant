"""리포트 공유/감사 라우트 호환 shim."""

from fastapi import APIRouter

from server.app.api.http.routes.report.audit import router as audit_router
from server.app.api.http.routes.report.sharing import router as sharing_router


router = APIRouter()
router.include_router(sharing_router)
router.include_router(audit_router)
