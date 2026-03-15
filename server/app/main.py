"""FastAPI 애플리케이션 진입점."""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware

from server.app.api.http.dependencies import (
    get_runtime_monitor_service,
    initialize_primary_persistence,
    preload_runtime_services,
    shutdown_live_stream_service,
    start_live_stream_service,
)
from server.app.api.http.wiring.persistence import describe_primary_persistence_target
from server.app.api.http.routes.audio_ws import router as audio_router
from server.app.api.http.routes.auth import router as auth_router
from server.app.api.http.routes.contexts import router as context_router
from server.app.api.http.routes.events import router as event_router
from server.app.api.http.routes.health import router as health_router
from server.app.api.http.routes.history import router as history_router
from server.app.api.http.routes.retrieval import router as retrieval_router
from server.app.api.http.routes.reports import router as report_router
from server.app.api.http.routes.session import router as session_router
from server.app.api.http.routes.text_ws import router as text_router
from server.app.core.config import settings
from server.app.core.logging import setup_logging
from server.app.core.runtime_readiness import reset_runtime_readiness


logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(_: FastAPI):
    """애플리케이션 수명주기 동안 필요한 리소스를 초기화한다."""

    setup_logging(
        level=settings.log_level,
        use_json=settings.log_json,
        log_file_path=settings.log_file_path,
    )
    logger.info(
        "애플리케이션 시작: env=%s debug=%s backend=%s target=%s",
        settings.app_env,
        settings.debug,
        settings.persistence_backend,
        describe_primary_persistence_target(),
    )
    reset_runtime_readiness(stt_preload_enabled=settings.stt_preload_on_startup)
    get_runtime_monitor_service().reset()
    initialize_primary_persistence()
    preload_runtime_services()
    await start_live_stream_service()
    yield
    await shutdown_live_stream_service()
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
app.include_router(auth_router)
app.include_router(context_router)
app.include_router(history_router)
app.include_router(retrieval_router)
app.include_router(session_router)
app.include_router(event_router)
app.include_router(report_router)
app.include_router(audio_router)
app.include_router(text_router)
