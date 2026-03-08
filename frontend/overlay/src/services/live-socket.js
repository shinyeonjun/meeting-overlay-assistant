import { buildWebSocketUrl } from "../config/runtime.js";

function buildLiveSocketPath(sessionId, source) {
    if (source === "dev_text") {
        return `/api/v1/ws/dev-text/${sessionId}`;
    }

    return `/api/v1/ws/audio/${sessionId}`;
}

export function openLiveSocket(sessionId, source, { onOpen, onClose, onError, onMessage }) {
    const wsUrl = buildWebSocketUrl(buildLiveSocketPath(sessionId, source));
    const socket = new WebSocket(wsUrl);

    socket.addEventListener("open", () => onOpen?.(socket));
    socket.addEventListener("close", () => onClose?.(socket));
    socket.addEventListener("error", () => onError?.(socket));
    socket.addEventListener("message", (event) => onMessage?.(event, socket));

    return socket;
}
