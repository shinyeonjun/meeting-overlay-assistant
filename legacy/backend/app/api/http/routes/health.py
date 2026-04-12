"""헬스 체크 라우트."""

from fastapi import APIRouter
from backend.app.core.runtime_readiness import get_runtime_readiness


router = APIRouter(tags=["health"])


@router.get("/health")
def health_check() -> dict[str, str]:
    """서버 상태를 반환한다."""
    return {"status": "ok"}


@router.get("/api/v1/runtime/readiness")
def runtime_readiness() -> dict[str, object]:
    """런타임 준비 상태를 반환한다."""

    return get_runtime_readiness()
