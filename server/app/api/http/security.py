"""HTTP/WebSocket 인증 보안 헬퍼."""

from __future__ import annotations

from fastapi import Depends, HTTPException, WebSocket, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from server.app.api.http.dependencies import get_auth_service
from server.app.core.config import settings
from server.app.contexts.identity import AuthenticatedRequest


bearer_scheme = HTTPBearer(auto_error=False)


def require_authenticated_session(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
) -> AuthenticatedRequest | None:
    """인증 활성화 시 Bearer 세션을 강제한다."""

    if not settings.auth_enabled:
        return None
    token = credentials.credentials if credentials is not None else None
    if token is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="인증이 필요합니다.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    auth_context = get_auth_service().authenticate(token)
    if auth_context is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="유효한 인증 세션이 아닙니다.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return auth_context


async def authenticate_websocket_if_required(
    websocket: WebSocket,
) -> AuthenticatedRequest | None:
    """인증 활성화 시 WebSocket 진입 전에 Bearer 세션을 확인한다."""

    if not settings.auth_enabled:
        return None

    token = _extract_websocket_token(websocket)
    if token is None:
        await websocket.close(code=4401, reason="인증이 필요합니다.")
        return None

    auth_context = get_auth_service().authenticate(token)
    if auth_context is None:
        await websocket.close(code=4401, reason="유효한 인증 세션이 아닙니다.")
        return None
    return auth_context


WEBSOCKET_AUTH_SUBPROTOCOL = "caps-auth"
WEBSOCKET_TOKEN_SUBPROTOCOL_PREFIX = "caps-token."


def _offered_subprotocols(websocket: WebSocket) -> list[str]:
    raw = websocket.headers.get("sec-websocket-protocol", "")
    return [item.strip() for item in raw.split(",") if item.strip()]


def accepted_websocket_subprotocol(websocket: WebSocket) -> str | None:
    """클라이언트가 인증 subprotocol을 제안했다면 그 이름을 돌려준다. 브라우저는 제안한 이름만 받아들인다."""

    if WEBSOCKET_AUTH_SUBPROTOCOL in _offered_subprotocols(websocket):
        return WEBSOCKET_AUTH_SUBPROTOCOL
    return None


def _extract_websocket_token(websocket: WebSocket) -> str | None:
    # 브라우저 WebSocket은 헤더를 붙일 수 없으므로 Sec-WebSocket-Protocol로 토큰을 받는다.
    # 쿼리스트링 토큰은 접근 로그와 프록시 로그에 남아서 받지 않는다.
    authorization_header = websocket.headers.get("authorization", "")
    if authorization_header.lower().startswith("bearer "):
        token = authorization_header[7:].strip()
        if token:
            return token

    for item in _offered_subprotocols(websocket):
        if item.startswith(WEBSOCKET_TOKEN_SUBPROTOCOL_PREFIX):
            token = item[len(WEBSOCKET_TOKEN_SUBPROTOCOL_PREFIX):].strip()
            if token:
                return token
    return None
