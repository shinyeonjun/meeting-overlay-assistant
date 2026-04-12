/** 오버레이 런타임에서 쓰는 runtime 설정을 정의한다. */
import { createApiBaseUrlStore } from "@caps-client-shared/runtime/create-api-base-url-store.js";

const controlRuntimeStore = createApiBaseUrlStore({
    defaultBaseUrl:
        import.meta.env.VITE_CONTROL_API_BASE_URL
        ?? import.meta.env.VITE_API_BASE_URL
        ?? "http://127.0.0.1:8011",
    storageKey: "caps-overlay-control-api-base-url",
});

const liveRuntimeStore = createApiBaseUrlStore({
    defaultBaseUrl:
        import.meta.env.VITE_LIVE_API_BASE_URL
        ?? "http://127.0.0.1:8012",
    storageKey: "caps-overlay-live-api-base-url",
});

export const buildApiUrl = controlRuntimeStore.buildApiUrl;
export const getApiBaseUrl = controlRuntimeStore.getApiBaseUrl;
export const setApiBaseUrl = controlRuntimeStore.setApiBaseUrl;

export const buildLiveApiUrl = liveRuntimeStore.buildApiUrl;
export const buildLiveWebSocketUrl = liveRuntimeStore.buildWebSocketUrl;
export const getLiveApiBaseUrl = liveRuntimeStore.getApiBaseUrl;
export const setLiveApiBaseUrl = liveRuntimeStore.setApiBaseUrl;
