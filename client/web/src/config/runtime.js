/** 웹 클라이언트의 runtime 모듈이다. */
import { createApiBaseUrlStore } from "@caps-client-shared/runtime/create-api-base-url-store.js";

const runtimeStore = createApiBaseUrlStore({
    defaultBaseUrl: import.meta.env.VITE_SERVER_BASE_URL ?? "http://127.0.0.1:8011",
    storageKey: "caps-web-server-base-url",
});

export function loadServerBaseUrl() {
    return runtimeStore.getApiBaseUrl();
}

export function saveServerBaseUrl(value) {
    return runtimeStore.setApiBaseUrl(value);
}

export const buildApiUrl = runtimeStore.buildApiUrl;
