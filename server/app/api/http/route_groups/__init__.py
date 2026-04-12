"""HTTP 계층에서 공통 관련   init   구성을 담당한다."""
from .control import include_control_routes
from .live import include_live_routes
from .shared import include_shared_routes

__all__ = [
    "include_control_routes",
    "include_live_routes",
    "include_shared_routes",
]
