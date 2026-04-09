"""FastAPI 애플리케이션 팩토리."""

from __future__ import annotations

import asyncio
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware

from server.app.api.http.dependencies import (
    get_runtime_monitor_service,
    get_session_recovery_service,
    initialize_primary_persistence,
    preload_runtime_services,
    shutdown_live_stream_service,
    start_live_stream_service,
)
from server.app.api.http.route_groups import (
    include_control_routes as include_control_route_group,
    include_live_routes as include_live_route_group,
    include_shared_routes,
)
from server.app.api.http.wiring.persistence import describe_primary_persistence_target
from server.app.core.config import settings
from server.app.core.logging import setup_logging
from server.app.core.runtime_readiness import reset_runtime_readiness

logger = logging.getLogger(__name__)


def _build_lifespan(*, enable_live_runtime: bool, enable_startup_recovery: bool):
    @asynccontextmanager
    async def lifespan(_: FastAPI):
        """애플리케이션 생명주기 동안 필요한 리소스를 초기화한다."""

        setup_logging(
            level=settings.log_level,
            use_json=settings.log_json,
            log_file_path=settings.log_file_path,
        )
        logger.info(
            "애플리케이션 시작: env=%s debug=%s backend=%s target=%s live_runtime=%s startup_recovery=%s",
            settings.app_env,
            settings.debug,
            "postgresql",
            describe_primary_persistence_target(),
            enable_live_runtime,
            enable_startup_recovery,
        )
        initialize_primary_persistence()

        if enable_startup_recovery and not enable_live_runtime:
            logger.warning(
                "live runtime 없이 startup session recovery를 실행합니다. control-only 단독 경로를 가정합니다."
            )

        recovery_task: asyncio.Task | None = None
        if enable_live_runtime:
            reset_runtime_readiness(stt_preload_enabled=settings.stt_preload_on_startup)
            get_runtime_monitor_service().reset()
            preload_runtime_services()
            await start_live_stream_service()

        if enable_startup_recovery:
            recovery_task = asyncio.create_task(
                get_session_recovery_service().recover_orphaned_running_sessions_async()
            )

        yield

        if recovery_task is not None and not recovery_task.done():
            recovery_task.cancel()
            try:
                await recovery_task
            except asyncio.CancelledError:
                pass

        if enable_live_runtime:
            await shutdown_live_stream_service()
        logger.info("애플리케이션 종료")

    return lifespan


def create_app(
    *,
    include_control_routes: bool,
    include_live_routes: bool,
    enable_live_runtime: bool | None = None,
    enable_startup_recovery: bool | None = None,
    process_report_jobs_inline: bool = False,
) -> FastAPI:
    """용도에 맞는 FastAPI 앱을 생성한다."""

    live_runtime_enabled = include_live_routes if enable_live_runtime is None else enable_live_runtime
    startup_recovery_enabled = (
        live_runtime_enabled if enable_startup_recovery is None else enable_startup_recovery
    )
    app = FastAPI(
        title=settings.app_name,
        debug=settings.debug,
        lifespan=_build_lifespan(
            enable_live_runtime=live_runtime_enabled,
            enable_startup_recovery=startup_recovery_enabled,
        ),
    )
    app.state.process_report_jobs_inline = process_report_jobs_inline
    app.state.enable_live_runtime = live_runtime_enabled
    app.state.enable_startup_recovery = startup_recovery_enabled
    app.add_middleware(
        CORSMiddleware,
        allow_origins=list(settings.cors_allowed_origins),
        allow_credentials=False,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.add_middleware(GZipMiddleware, minimum_size=1024)

    include_shared_routes(app)

    if include_control_routes:
        include_control_route_group(app)

    if include_live_routes:
        include_live_route_group(app)

    return app
