"""FastAPI 애플리케이션 진입점."""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware

from backend.app.api.http.dependencies import preload_runtime_services
from backend.app.api.http.routes.audio_ws import router as audio_router
from backend.app.api.http.routes.events import router as event_router
from backend.app.api.http.routes.health import router as health_router
from backend.app.api.http.routes.reports import router as report_router
from backend.app.api.http.routes.sessions import router as session_router
from backend.app.api.http.routes.text_ws import router as text_router
from backend.app.core.config import settings
from backend.app.core.logging import setup_logging
from backend.app.core.runtime_readiness import reset_runtime_readiness
from backend.app.infrastructure.persistence.sqlite.database import database


logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(_: FastAPI):
    """애플리케이션 수명주기 동안 필요한 리소스를 초기화한다."""

    setup_logging(level=settings.log_level, use_json=settings.log_json)
    logger.info(
        "애플리케이션 시작: env=%s debug=%s database=%s",
        settings.app_env,
        settings.debug,
        settings.database_path,
    )
    reset_runtime_readiness(stt_preload_enabled=settings.stt_preload_on_startup)
    database.initialize()
    preload_runtime_services()
    yield
    logger.info("애플리케이션 종료")


app = FastAPI(title=settings.app_name, debug=settings.debug, lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=list(settings.cors_allowed_origins),
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(GZipMiddleware, minimum_size=1024)

app.include_router(health_router)
app.include_router(session_router)
app.include_router(event_router)
app.include_router(report_router)
app.include_router(audio_router)
app.include_router(text_router)
