import { getApiBaseUrl } from "../../config/runtime.js";
import { elements } from "../../dom/elements.js";
import { appState } from "../../state/app-state.js";
import { hydrateAuthState, setAutoLoginEnabled } from "../../state/auth-store.js";
import {
    renderAutoLoginChoice,
    renderHeaderSummary,
} from "./auth-renderer.js";
import {
    handleLogout,
    handleAuthExpired,
    handleLoginSubmit,
    refreshAuthState,
    setAuthReadyCallback,
} from "./auth-session-controller.js";

let authEventsBound = false;

export async function initializeAuthFlow({ onReady }) {
    setAuthReadyCallback(onReady);
    hydrateAuthState(appState);

    if (elements.serverUrlInput) {
        elements.serverUrlInput.value = appState.auth.serverUrl ?? getApiBaseUrl();
    }

    renderHeaderSummary();
    renderAutoLoginChoice();
    bindAuthEvents();
    await refreshAuthState({ preferStoredSession: true });
}

function bindAuthEvents() {
    if (authEventsBound) {
        return;
    }

    elements.authRefreshButton?.addEventListener("click", () => {
        void refreshAuthState({ preferStoredSession: true });
    });
    elements.authLoginForm?.addEventListener("submit", (event) => {
        void handleLoginSubmit(event);
    });
    elements.authRememberCheckbox?.addEventListener("change", () => {
        setAutoLoginEnabled(appState, elements.authRememberCheckbox.checked);
    });
    elements.logoutButton?.addEventListener("click", () => {
        void handleLogout();
    });
    window.addEventListener("caps-auth-expired", () => {
        void handleAuthExpired();
    });

    authEventsBound = true;
}
