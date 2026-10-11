"""비정상 종료 세션 복구 서비스."""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timedelta, timezone

from server.app.core.config import settings
from server.app.domain.session import MeetingSession
from server.app.domain.session.runtime_liveness import RuntimeLivenessPolicy
from server.app.domain.shared.enums import SessionStatus
from server.app.repositories.contracts.session import SessionRepository

logger = logging.getLogger(__name__)


def _liveness_policy() -> RuntimeLivenessPolicy:
    return RuntimeLivenessPolicy(stale_after=timedelta(seconds=settings.session_runtime_stale_seconds))


def _now() -> datetime:
    return datetime.now(timezone.utc)


class SessionRecoveryService:
    """고아 running 세션을 복구 필요 상태로 정리한다.

    control API와 live API는 다른 프로세스일 수 있으므로, 세션이 살아 있는지는
    DB에 찍힌 런타임 하트비트로 판단한다. 같은 프로세스의 WebSocket 컨텍스트는
    하트비트가 아직 찍히기 전이라도 살아 있는 근거로 본다.
    """

    def __init__(
        self,
        *,
        session_repository: SessionRepository,
        live_stream_service,
    ) -> None:
        self._session_repository = session_repository
        self._live_stream_service = live_stream_service

    async def recover_orphaned_running_sessions_async(self, *, limit: int = 500) -> int:
        """앱 시작 시 고아 running 세션을 비동기로 정리한다."""

        return await asyncio.to_thread(
            self.recover_orphaned_running_sessions,
            limit=limit,
        )

    def recover_orphaned_running_sessions(self, *, limit: int = 500) -> int:
        """하트비트가 끊긴 running 세션을 정리한다."""

        recovered_count = 0
        candidates = self._session_repository.list_running_with_stale_heartbeat(
            heartbeat_cutoff=_liveness_policy().heartbeat_cutoff(_now()).isoformat(),
            limit=limit,
        )
        for session in candidates:
            if self._live_stream_service.has_session_contexts(session.id):
                continue
            recovered = self._mark_runtime_lost(session.id)
            if recovered is not None:
                recovered_count += 1

        if recovered_count > 0:
            logger.warning(
                "비정상 종료 세션 자동 복구 완료: recovered_count=%s",
                recovered_count,
            )
        else:
            logger.info("비정상 종료 세션 자동 복구 대상이 없습니다.")
        return recovered_count

    def recover_session_if_orphaned(self, session_id: str) -> MeetingSession | None:
        """mutation 액션 직전에 running 고아 세션을 정리한다."""

        session = self._session_repository.get_by_id(session_id)
        if session is None:
            return None
        if session.status != SessionStatus.RUNNING:
            return session
        orphaned = _liveness_policy().is_orphaned(
            status=session.status,
            has_local_context=self._live_stream_service.has_session_contexts(session.id),
            last_heartbeat_at=self._session_repository.get_runtime_heartbeat_at(session.id),
            now=_now(),
        )
        if not orphaned:
            return session

        recovered = self._mark_runtime_lost(session.id)
        if recovered is not None:
            logger.warning(
                "고아 running 세션을 mutation 직전에 복구했습니다: session_id=%s",
                session_id,
            )
            return recovered
        return self._session_repository.get_by_id(session_id)

    def _mark_runtime_lost(self, session_id: str) -> MeetingSession | None:
        """런타임 손실 세션을 ended + recovery_required 상태로 전이한다."""

        session = self._session_repository.get_by_id(session_id)
        if session is None:
            return None
        if session.status != SessionStatus.RUNNING:
            return session

        marked_session = session.mark_recovery_required("runtime_lost")
        updated = self._session_repository.mark_recovery_required_if_running(
            session_id,
            recovery_reason=marked_session.recovery_reason or "runtime_lost",
            recovery_detected_at=marked_session.recovery_detected_at or marked_session.ended_at or marked_session.started_at,
        )
        return updated or self._session_repository.get_by_id(session_id)
