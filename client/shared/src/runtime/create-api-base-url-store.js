function canUseLocalStorage() {
    return typeof window !== "undefined" && typeof window.localStorage !== "undefined";
}

function normalizeApiBaseUrl(rawValue, fallbackValue) {
    let normalized = String(rawValue ?? fallbackValue).trim() || fallbackValue;
    if (!/^https?:\/\//i.test(normalized)) {
        normalized = `http://${normalized}`;
    }
    return normalized.replace(/\/+$/, "");
}

export function createApiBaseUrlStore({
    defaultBaseUrl,
    storageKey,
}) {
    const normalizedDefaultBaseUrl = normalizeApiBaseUrl(defaultBaseUrl, "http://127.0.0.1:8011");
    let apiBaseUrl = loadPersistedApiBaseUrl();

    function buildApiUrl(pathname = "") {
        const normalizedPath = pathname.startsWith("/") || pathname === "" ? pathname : `/${pathname}`;
        return `${apiBaseUrl}${normalizedPath}`;
    }

    function buildWebSocketUrl(pathname = "") {
        const websocketBaseUrl = apiBaseUrl.replace(/^http/i, "ws");
        const normalizedPath = pathname.startsWith("/") || pathname === "" ? pathname : `/${pathname}`;
        return `${websocketBaseUrl}${normalizedPath}`;
    }

    function getApiBaseUrl() {
        return apiBaseUrl;
    }

    function setApiBaseUrl(nextBaseUrl) {
        apiBaseUrl = normalizeApiBaseUrl(nextBaseUrl, normalizedDefaultBaseUrl);
        persistApiBaseUrl(apiBaseUrl);
        return apiBaseUrl;
    }

    function loadPersistedApiBaseUrl() {
        if (!canUseLocalStorage()) {
            return normalizedDefaultBaseUrl;
        }

        const persistedValue = window.localStorage.getItem(storageKey);
        return normalizeApiBaseUrl(persistedValue || normalizedDefaultBaseUrl, normalizedDefaultBaseUrl);
    }

    function persistApiBaseUrl(nextBaseUrl) {
        if (!canUseLocalStorage()) {
            return;
        }
        window.localStorage.setItem(storageKey, nextBaseUrl);
    }

    return {
        buildApiUrl,
        buildWebSocketUrl,
        getApiBaseUrl,
        loadPersistedApiBaseUrl,
        setApiBaseUrl,
    };
}
