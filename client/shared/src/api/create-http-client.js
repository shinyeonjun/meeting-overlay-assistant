export function createHttpClient({
    buildApiUrl,
    getAccessToken,
    clearAuthSession,
    dispatchAuthExpired,
    fetchImpl = fetch,
}) {
    async function handleResponse(response, url, includeAuth) {
        if (response.status === 401 && includeAuth) {
            clearAuthSession?.();
            dispatchAuthExpired?.();
            throw new Error(`HTTP 401: ${url}`);
        }

        if (!response.ok) {
            throw new Error(`HTTP ${response.status}: ${url}`);
        }

        return response;
    }

    function buildRequestOptions(fetchOptions, includeAuth) {
        const headers = new Headers(fetchOptions.headers ?? {});
        if (includeAuth) {
            const accessToken = getAccessToken?.();
            if (accessToken) {
                headers.set("Authorization", `Bearer ${accessToken}`);
            }
        }

        return {
            ...fetchOptions,
            headers,
        };
    }

    async function requestJson(url, options = {}) {
        const {
            includeAuth = true,
            ...fetchOptions
        } = options;

        const response = await fetchImpl(buildApiUrl(url), buildRequestOptions(fetchOptions, includeAuth));
        const handledResponse = await handleResponse(response, url, includeAuth);
        return handledResponse.json();
    }

    async function requestNoContent(url, options = {}) {
        const {
            includeAuth = true,
            ...fetchOptions
        } = options;

        const response = await fetchImpl(buildApiUrl(url), buildRequestOptions(fetchOptions, includeAuth));
        await handleResponse(response, url, includeAuth);
    }

    return {
        requestJson,
        requestNoContent,
    };
}
