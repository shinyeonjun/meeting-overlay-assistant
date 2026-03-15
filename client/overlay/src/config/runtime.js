const DEFAULT_API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "http://127.0.0.1:8011";
const API_BASE_URL_STORAGE_KEY = "caps-overlay-api-base-url";

let apiBaseUrl = loadPersistedApiBaseUrl();

export function buildApiUrl(pathname) {
    return `${apiBaseUrl}${pathname}`;
}

export function buildWebSocketUrl(pathname) {
    const websocketBaseUrl = apiBaseUrl.replace(/^http/i, "ws");
    return `${websocketBaseUrl}${pathname}`;
}

export function getApiBaseUrl() {
    return apiBaseUrl;
}

export function setApiBaseUrl(nextBaseUrl) {
    apiBaseUrl = normalizeApiBaseUrl(nextBaseUrl);
    persistApiBaseUrl(apiBaseUrl);
    return apiBaseUrl;
}

function loadPersistedApiBaseUrl() {
    if (!canUseLocalStorage()) {
        return normalizeApiBaseUrl(DEFAULT_API_BASE_URL);
    }

    const persistedValue = window.localStorage.getItem(API_BASE_URL_STORAGE_KEY);
    return normalizeApiBaseUrl(persistedValue || DEFAULT_API_BASE_URL);
}

function persistApiBaseUrl(nextBaseUrl) {
    if (!canUseLocalStorage()) {
        return;
    }
    window.localStorage.setItem(API_BASE_URL_STORAGE_KEY, nextBaseUrl);
}

function normalizeApiBaseUrl(rawValue) {
    const fallbackValue = String(DEFAULT_API_BASE_URL).trim();
    let normalized = String(rawValue ?? fallbackValue).trim() || fallbackValue;
    if (!/^https?:\/\//i.test(normalized)) {
        normalized = `http://${normalized}`;
    }
    return normalized.replace(/\/+$/, "");
}

function canUseLocalStorage() {
    return typeof window !== "undefined" && typeof window.localStorage !== "undefined";
}
