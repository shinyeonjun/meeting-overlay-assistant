"""진행 중 회의가 아직 살아 있는지 판단하는 정책.

live 런타임은 다른 프로세스에 있을 수 있으므로, 이 프로세스가 직접 볼 수 없다.
그래서 "살아 있음"은 두 가지 근거로만 판단한다.
- 이 프로세스에 런타임 컨텍스트가 있다.
- 런타임이 주기적으로 찍은 하트비트가 기준 시간 안에 있다.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta

from server.app.domain.shared.enums import SessionStatus


@dataclass(frozen=True)
class RuntimeLivenessPolicy:
    stale_after: timedelta

    def heartbeat_cutoff(self, now: datetime) -> datetime:
        """이 시각보다 오래된 하트비트는 살아 있는 런타임의 것이 아니다."""

        return now - self.stale_after

    def is_orphaned(
        self,
        *,
        status: SessionStatus,
        has_local_context: bool,
        last_heartbeat_at: str | None,
        now: datetime,
    ) -> bool:
        if status != SessionStatus.RUNNING:
            return False
        if has_local_context:
            return False
        if last_heartbeat_at is None:
            return True
        return datetime.fromisoformat(last_heartbeat_at) <= self.heartbeat_cutoff(now)
