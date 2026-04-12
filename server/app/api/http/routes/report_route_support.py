"""리포트 라우트 공통 함수 호환 shim."""

from server.app.api.http.routes.report.support import (
    require_auth_context,
    to_latest_report_response,
    to_report_item_response,
    to_report_share_inbox_item_response,
    to_report_share_response,
)

__all__ = [
    "require_auth_context",
    "to_latest_report_response",
    "to_report_item_response",
    "to_report_share_inbox_item_response",
    "to_report_share_response",
]
