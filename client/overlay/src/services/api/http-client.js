/** 오버레이에서 공통 관련 http client 서비스를 제공한다. */
import { createHttpClient } from "@caps-client-shared/api/create-http-client.js";

import { buildApiUrl, buildLiveApiUrl } from "../../config/runtime.js";
import {
    clearPersistedAuthSession,
    dispatchAuthExpired,
    getPersistedAccessToken,
} from "../auth-storage.js";

const httpClient = createHttpClient({
    buildApiUrl,
    getAccessToken: getPersistedAccessToken,
    clearAuthSession: clearPersistedAuthSession,
    dispatchAuthExpired,
});

const liveHttpClient = createHttpClient({
    buildApiUrl: buildLiveApiUrl,
    getAccessToken: getPersistedAccessToken,
    clearAuthSession: clearPersistedAuthSession,
    dispatchAuthExpired,
});

export const requestJson = httpClient.requestJson;
export const requestNoContent = httpClient.requestNoContent;
export const requestLiveJson = liveHttpClient.requestJson;
