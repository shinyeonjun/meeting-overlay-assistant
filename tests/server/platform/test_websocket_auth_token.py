"""WebSocket 인증 토큰은 쿼리스트링이 아니라 Sec-WebSocket-Protocol로만 받는다."""

from __future__ import annotations

from starlette.websockets import WebSocket

from server.app.api.http.security import (
    accepted_websocket_subprotocol,
    _extract_websocket_token,
)


def _socket(headers: list[tuple[bytes, bytes]], query: bytes = b"") -> WebSocket:
    scope = {
        "type": "websocket",
        "path": "/api/v1/ws/audio/session-1",
        "query_string": query,
        "headers": headers,
    }
    return WebSocket(scope, receive=None, send=None)


def test_subprotocol로_온_토큰을_읽고_caps_auth를_선택한다():
    socket = _socket([(b"sec-websocket-protocol", b"caps-auth, caps-token.abc123")])

    assert _extract_websocket_token(socket) == "abc123"
    assert accepted_websocket_subprotocol(socket) == "caps-auth"


def test_쿼리스트링_토큰은_받지_않는다():
    socket = _socket([], query=b"token=leaked")

    assert _extract_websocket_token(socket) is None
