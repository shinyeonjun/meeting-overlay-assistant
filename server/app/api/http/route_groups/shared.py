"""HTTP 계층에서 공통 관련 shared 구성을 담당한다."""
from __future__ import annotations

from fastapi import FastAPI

from server.app.api.http.routes.health import router as health_router


def include_shared_routes(app: FastAPI) -> None:
    """공통 라우트를 앱에 등록한다."""

    app.include_router(health_router)
