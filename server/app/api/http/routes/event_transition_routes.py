"""이전 이벤트 상태 전이 라우트 경로 호환용 shim."""

from server.app.api.http.routes.events.transition import router

__all__ = ["router"]
