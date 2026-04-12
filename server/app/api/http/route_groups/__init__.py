"""HTTP 라우트 그룹 조립기."""

from .control import include_control_routes
from .live import include_live_routes
from .shared import include_shared_routes

__all__ = [
    "include_control_routes",
    "include_live_routes",
    "include_shared_routes",
]
