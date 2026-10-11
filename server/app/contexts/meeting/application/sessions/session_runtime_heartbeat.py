"""live 프로세스가 진행 중 세션의 런타임 하트비트를 DB에 찍는 주기 작업."""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone

logger = logging.getLogger(__name__)


async def run_session_runtime_heartbeat(
    *,
    live_stream_service,
    session_repository,
    interval_seconds: float,
) -> None:
    """이 프로세스에 live context가 붙은 세션의 하트비트를 주기적으로 갱신한다.

    control API 프로세스는 이 컨텍스트를 볼 수 없으므로, 여기서 찍힌 하트비트로 세션이 살아 있는지 판단한다.
    """

    while True:
        await asyncio.sleep(interval_seconds)
        session_ids = live_stream_service.active_session_ids()
        if not session_ids:
            continue
        try:
            await asyncio.to_thread(
                session_repository.touch_runtime_heartbeat,
                session_ids,
                heartbeat_at=datetime.now(timezone.utc).isoformat(),
            )
        except Exception:
            logger.exception("세션 런타임 하트비트 갱신 실패: session_count=%s", len(session_ids))
