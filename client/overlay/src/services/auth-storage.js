/** 오버레이에서 공통 관련 auth storage 서비스를 제공한다. */
import { createAuthSessionStore } from "@caps-client-shared/auth/create-auth-session-store.js";

const authSessionStore = createAuthSessionStore({
    storageKey: "caps-overlay-auth-session",
    expiredEventName: "caps-auth-expired",
});

export const clearPersistedAuthSession = authSessionStore.clearPersistedAuthSession;
export const dispatchAuthExpired = authSessionStore.dispatchAuthExpired;
export const getPersistedAccessToken = authSessionStore.getPersistedAccessToken;
export const loadPersistedAuthSession = authSessionStore.loadPersistedAuthSession;
export const persistAuthSession = authSessionStore.persistAuthSession;
