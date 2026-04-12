"""HTTP 계층에서 공통 관련 health 구성을 담당한다."""
from fastapi import APIRouter


router = APIRouter(tags=["health"])


@router.get("/health")
def health_check() -> dict[str, str]:
    """서버 헬스 상태를 반환한다."""

    return {"status": "ok"}
