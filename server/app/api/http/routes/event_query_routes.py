"""이전 이벤트 조회 라우트 경로 호환용 shim."""

from server.app.api.http.routes.events.query import router

__all__ = ["router"]
