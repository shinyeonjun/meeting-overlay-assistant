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

// 예전 버전이 문자열로 저장해 둔 값 중 "기본값을 그대로 저장한 것"으로 보는 주소.
// 사용자가 직접 바꾼 값이 아니므로, 지금 기본값(환경 변수)과 다르면 버린다.
const BUILT_IN_DEFAULT_BASE_URLS = new Set([
    "http://127.0.0.1:8011",
    "http://127.0.0.1:8012",
    "http://localhost:8011",
    "http://localhost:8012",
]);

/**
 * 서버 주소를 기억하는 저장소.
 *
 * - 기본값(빌드 환경 변수)과 같은 주소는 저장하지 않는다. 그래야 기본값이 바뀌면 그대로 따라간다.
 * - 사용자가 다른 주소를 고르면 그때의 기본값과 함께 저장한다. 나중에 기본값이 바뀌면 옛 저장값은 버린다.
 */
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

    function getDefaultApiBaseUrl() {
        return normalizedDefaultBaseUrl;
    }

    function isUsingDefaultApiBaseUrl() {
        return apiBaseUrl === normalizedDefaultBaseUrl;
    }

    function setApiBaseUrl(nextBaseUrl) {
        apiBaseUrl = normalizeApiBaseUrl(nextBaseUrl, normalizedDefaultBaseUrl);
        persistApiBaseUrl(apiBaseUrl);
        return apiBaseUrl;
    }

    function resetApiBaseUrl() {
        return setApiBaseUrl(normalizedDefaultBaseUrl);
    }

    function loadPersistedApiBaseUrl() {
        if (!canUseLocalStorage()) {
            return normalizedDefaultBaseUrl;
        }

        const stored = readStoredEntry();
        if (!stored) {
            return normalizedDefaultBaseUrl;
        }
        if (stored.defaultAtSave !== null && stored.defaultAtSave !== normalizedDefaultBaseUrl) {
            // 저장한 뒤 기본값(환경 변수)이 바뀌었다. 새 기본값을 따른다.
            window.localStorage.removeItem(storageKey);
            return normalizedDefaultBaseUrl;
        }
        if (stored.defaultAtSave === null && BUILT_IN_DEFAULT_BASE_URLS.has(stored.value)) {
            window.localStorage.removeItem(storageKey);
            return normalizedDefaultBaseUrl;
        }
        return stored.value;
    }

    function readStoredEntry() {
        const raw = window.localStorage.getItem(storageKey);
        if (!raw) {
            return null;
        }
        try {
            const parsed = JSON.parse(raw);
            if (parsed && typeof parsed.value === "string") {
                return {
                    value: normalizeApiBaseUrl(parsed.value, normalizedDefaultBaseUrl),
                    defaultAtSave: typeof parsed.defaultAtSave === "string"
                        ? normalizeApiBaseUrl(parsed.defaultAtSave, normalizedDefaultBaseUrl)
                        : null,
                };
            }
        } catch {
            // 예전 버전은 주소 문자열을 그대로 저장했다.
        }
        return { value: normalizeApiBaseUrl(raw, normalizedDefaultBaseUrl), defaultAtSave: null };
    }

    function persistApiBaseUrl(nextBaseUrl) {
        if (!canUseLocalStorage()) {
            return;
        }
        if (nextBaseUrl === normalizedDefaultBaseUrl) {
            window.localStorage.removeItem(storageKey);
            return;
        }
        window.localStorage.setItem(
            storageKey,
            JSON.stringify({ value: nextBaseUrl, defaultAtSave: normalizedDefaultBaseUrl }),
        );
    }

    return {
        buildApiUrl,
        buildWebSocketUrl,
        getApiBaseUrl,
        getDefaultApiBaseUrl,
        isUsingDefaultApiBaseUrl,
        loadPersistedApiBaseUrl,
        resetApiBaseUrl,
        setApiBaseUrl,
    };
}
