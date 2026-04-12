"""HTTP 계층에서 공통 관련 control 구성을 담당한다."""
from __future__ import annotations

from fastapi import FastAPI

from server.app.api.http.routes.auth import router as auth_router
from server.app.api.http.routes.contexts import router as context_router
from server.app.api.http.routes.events import router as event_router
from server.app.api.http.routes.history import router as history_router
from server.app.api.http.routes.report import router as report_router
from server.app.api.http.routes.retrieval import router as retrieval_router
from server.app.api.http.routes.session import router as session_router
from server.app.api.http.routes.workspace import router as workspace_router


def include_control_routes(app: FastAPI) -> None:
    """Control API 라우트를 앱에 등록한다."""

    app.include_router(auth_router)
    app.include_router(context_router)
    app.include_router(history_router)
    app.include_router(retrieval_router)
    app.include_router(workspace_router)
    app.include_router(session_router)
    app.include_router(event_router)
    app.include_router(report_router)
