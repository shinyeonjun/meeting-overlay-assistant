"""HTTP 계층에서 참여자 관련   init   구성을 담당한다."""
from server.app.api.http.routes.participation.followups import router as followups_router
from server.app.api.http.routes.participation.resolution import router

__all__ = ["followups_router", "router"]
