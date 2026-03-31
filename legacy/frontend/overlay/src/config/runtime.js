export const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "http://127.0.0.1:8000";

export function buildApiUrl(pathname) {
    return `${API_BASE_URL}${pathname}`;
}

export function buildWebSocketUrl(pathname) {
    const websocketBaseUrl = API_BASE_URL.replace(/^http/i, "ws");
    return `${websocketBaseUrl}${pathname}`;
}
