import { buildLiveWebSocketUrl } from "../config/runtime.js";
import { getPersistedAccessToken } from "./auth-storage.js";

// 토큰은 URL이 아니라 Sec-WebSocket-Protocol로 보낸다. 서버는 "caps-auth"를 골라 응답한다.
const WEBSOCKET_AUTH_SUBPROTOCOL = "caps-auth";
const WEBSOCKET_TOKEN_SUBPROTOCOL_PREFIX = "caps-token.";

function buildLiveSocketPath(sessionId, source) {
    if (source === "text_input") {
        return `/api/v1/ws/text/${sessionId}`;
    }
    return `/api/v1/ws/audio/${sessionId}`;
}

function buildLiveSocketProtocols() {
    const accessToken = getPersistedAccessToken();
    if (!accessToken) {
        return undefined;
    }
    return [WEBSOCKET_AUTH_SUBPROTOCOL, `${WEBSOCKET_TOKEN_SUBPROTOCOL_PREFIX}${accessToken}`];
}

export function openLiveSocket(sessionId, source, { onOpen, onClose, onError, onMessage }) {
    const wsUrl = buildLiveWebSocketUrl(buildLiveSocketPath(sessionId, source));
    const socket = new WebSocket(wsUrl, buildLiveSocketProtocols());

    socket.addEventListener("open", () => onOpen?.(socket));
    socket.addEventListener("close", () => onClose?.(socket));
    socket.addEventListener("error", () => onError?.(socket));
    socket.addEventListener("message", (event) => onMessage?.(event, socket));

    return socket;
}
