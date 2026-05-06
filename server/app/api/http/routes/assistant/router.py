"""assistant 라우트 진입점."""

from fastapi import APIRouter, Depends

from server.app.api.http.routes.assistant.chat import router as chat_router
from server.app.api.http.security import require_authenticated_session

router = APIRouter(
    prefix="/api/v1/assistant",
    tags=["assistant"],
    dependencies=[Depends(require_authenticated_session)],
)

router.include_router(chat_router)
