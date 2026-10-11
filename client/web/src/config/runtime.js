import { createApiBaseUrlStore } from "@caps-client-shared/runtime/create-api-base-url-store.js";

const runtimeStore = createApiBaseUrlStore({
    defaultBaseUrl: import.meta.env.VITE_SERVER_BASE_URL ?? "http://127.0.0.1:8011",
    storageKey: "caps-web-server-base-url",
});

export const buildApiUrl = runtimeStore.buildApiUrl;
