import { buildApiUrl } from "../../config/runtime.js";
import {
    clearPersistedAuthSession,
    dispatchAuthExpired,
    getPersistedAccessToken,
} from "../auth-storage.js";

async function handleResponse(response, url, includeAuth) {
    if (response.status === 401 && includeAuth) {
        clearPersistedAuthSession();
        dispatchAuthExpired();
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
        const accessToken = getPersistedAccessToken();
        if (accessToken) {
            headers.set("Authorization", `Bearer ${accessToken}`);
        }
    }

    return {
        ...fetchOptions,
        headers,
    };
}

export async function requestJson(url, options = {}) {
    const {
        includeAuth = true,
        ...fetchOptions
    } = options;

    const response = await fetch(buildApiUrl(url), buildRequestOptions(fetchOptions, includeAuth));
    const handledResponse = await handleResponse(response, url, includeAuth);
    return handledResponse.json();
}

export async function requestNoContent(url, options = {}) {
    const {
        includeAuth = true,
        ...fetchOptions
    } = options;

    const response = await fetch(buildApiUrl(url), buildRequestOptions(fetchOptions, includeAuth));
    await handleResponse(response, url, includeAuth);
}
