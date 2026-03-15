import { buildWebSocketUrl } from "../config/runtime.js";
import { getPersistedAccessToken } from "./auth-storage.js";

function buildLiveSocketPath(sessionId, source) {
    const searchParams = new URLSearchParams();
    const accessToken = getPersistedAccessToken();
    if (accessToken) {
        searchParams.set("token", accessToken);
    }

    if (source === "text_input") {
        const query = searchParams.toString();
        return `/api/v1/ws/text/${sessionId}${query ? `?${query}` : ""}`;
    }

    const query = searchParams.toString();
    return `/api/v1/ws/audio/${sessionId}${query ? `?${query}` : ""}`;
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
