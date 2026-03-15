"""HTTP/WebSocket 인증 보안 헬퍼."""

from __future__ import annotations

from fastapi import Depends, HTTPException, WebSocket, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from server.app.api.http.dependencies import get_auth_service
from server.app.core.config import settings
from server.app.domain.models.auth_session import AuthenticatedSession


bearer_scheme = HTTPBearer(auto_error=False)


def require_authenticated_session(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
) -> AuthenticatedSession | None:
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
) -> AuthenticatedSession | None:
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


def _extract_websocket_token(websocket: WebSocket) -> str | None:
    authorization_header = websocket.headers.get("authorization", "")
    if authorization_header.lower().startswith("bearer "):
        token = authorization_header[7:].strip()
        if token:
            return token

    query_token = websocket.query_params.get("token") or websocket.query_params.get("access_token")
    if query_token:
        return query_token.strip()
    return None
