"""HTTP 계층에서 공통 관련 live 구성을 담당한다."""
from __future__ import annotations

from fastapi import FastAPI

from server.app.api.http.routes.audio_ws import router as audio_router
from server.app.api.http.routes.runtime import router as runtime_router
from server.app.api.http.routes.text_ws import router as text_router


def include_live_routes(app: FastAPI) -> None:
    """Live API 라우트를 앱에 등록한다."""

    app.include_router(runtime_router)
    app.include_router(audio_router)
    app.include_router(text_router)
