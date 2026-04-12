"""영속성 계층 공통 타입."""

from __future__ import annotations

from contextlib import AbstractContextManager
from typing import Any, Protocol, TypeAlias


ConnectionLike: TypeAlias = Any


class TransactionManager(Protocol):
    """트랜잭션 컨텍스트를 제공하는 객체 계약."""

    def transaction(self) -> AbstractContextManager[ConnectionLike]:
        """연결 범위를 감싸는 컨텍스트 매니저를 반환한다."""
