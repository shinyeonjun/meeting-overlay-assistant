import { getApiBaseUrl, getLiveApiBaseUrl } from "../config/runtime.js";
import {
    clearPersistedAuthSession,
    loadPersistedAuthSession,
    persistAuthSession,
} from "../services/auth-storage.js";

export function hydrateAuthState(state) {
    const persistedSession = loadPersistedAuthSession();
    state.auth.serverUrl = getApiBaseUrl();
    state.auth.liveServerUrl = getLiveApiBaseUrl();
    state.auth.accessToken = persistedSession.accessToken;
    state.auth.user = persistedSession.user;
    state.auth.autoLoginEnabled = persistedSession.autoLoginEnabled !== false;
}

export function applyAuthConfig(state, payload) {
    state.auth.initialized = true;
    state.auth.authEnabled = payload.enabled === true;
    state.auth.bootstrapRequired = payload.bootstrap_required === true;
    state.auth.userCount = Number(payload.user_count ?? 0);
}

export function setAuthServerUrls(state, { serverUrl, liveServerUrl }) {
    state.auth.serverUrl = serverUrl;
    state.auth.liveServerUrl = liveServerUrl;
}

export function setAuthenticatedSession(state, { accessToken, user }) {
    state.auth.accessToken = accessToken;
    state.auth.user = user;
    persistAuthSession({
        accessToken,
        user,
        autoLoginEnabled: state.auth.autoLoginEnabled !== false,
    });
}

export function clearAuthenticatedSession(state) {
    state.auth.accessToken = null;
    state.auth.user = null;
    clearPersistedAuthSession();
}

export function setAutoLoginEnabled(state, enabled) {
    state.auth.autoLoginEnabled = enabled !== false;
}

export function isAuthenticated(state) {
    return Boolean(state.auth.accessToken && state.auth.user);
}
