"""모든 엔트리포인트가 공통으로 쓰는 라우트 그룹."""

from __future__ import annotations

from fastapi import FastAPI

from server.app.api.http.routes.health import router as health_router


def include_shared_routes(app: FastAPI) -> None:
    """공통 라우트를 앱에 등록한다."""

    app.include_router(health_router)
