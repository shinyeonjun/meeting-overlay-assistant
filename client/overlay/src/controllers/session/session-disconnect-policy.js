const DISCONNECT_STATUS_PREFIXES = [
    "HTTP 404:",
    "HTTP 410:",
    "HTTP 502:",
    "HTTP 503:",
    "HTTP 504:",
];

export function shouldTreatAsUnexpectedSessionDisconnect(error) {
    const message = String(error?.message ?? "").trim();
    if (!message) {
        return false;
    }

    if (error instanceof TypeError) {
        return true;
    }

    if (
        message.includes("Failed to fetch")
        || message.includes("NetworkError")
        || message.includes("WebSocket is closed")
    ) {
        return true;
    }

    return DISCONNECT_STATUS_PREFIXES.some((prefix) => message.startsWith(prefix));
}
