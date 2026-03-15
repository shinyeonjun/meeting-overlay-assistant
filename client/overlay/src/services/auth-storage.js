const AUTH_SESSION_STORAGE_KEY = "caps-overlay-auth-session";
let inMemoryAuthSession = {
    accessToken: null,
    user: null,
};

export function loadPersistedAuthSession() {
    if (!canUseLocalStorage()) {
        return {
            accessToken: null,
            user: null,
            autoLoginEnabled: true,
        };
    }

    try {
        const rawValue = window.localStorage.getItem(AUTH_SESSION_STORAGE_KEY);
        if (!rawValue) {
            inMemoryAuthSession = {
                accessToken: null,
                user: null,
            };
            return {
                accessToken: null,
                user: null,
                autoLoginEnabled: true,
            };
        }
        const parsed = JSON.parse(rawValue);
        const session = {
            accessToken: typeof parsed?.accessToken === "string" ? parsed.accessToken : null,
            user: parsed?.user && typeof parsed.user === "object" ? parsed.user : null,
            autoLoginEnabled: parsed?.autoLoginEnabled !== false,
        };
        inMemoryAuthSession = {
            accessToken: session.accessToken,
            user: session.user,
        };
        return session;
    } catch {
        inMemoryAuthSession = {
            accessToken: null,
            user: null,
        };
        return {
            accessToken: null,
            user: null,
            autoLoginEnabled: true,
        };
    }
}

export function persistAuthSession({ accessToken, user, autoLoginEnabled = true }) {
    inMemoryAuthSession = {
        accessToken,
        user,
    };

    if (!canUseLocalStorage()) {
        return;
    }

    window.localStorage.setItem(
        AUTH_SESSION_STORAGE_KEY,
        JSON.stringify({
            accessToken: autoLoginEnabled ? accessToken : null,
            user: autoLoginEnabled ? user : null,
            autoLoginEnabled,
        }),
    );
}

export function clearPersistedAuthSession() {
    inMemoryAuthSession = {
        accessToken: null,
        user: null,
    };
    if (!canUseLocalStorage()) {
        return;
    }
    window.localStorage.removeItem(AUTH_SESSION_STORAGE_KEY);
}

export function getPersistedAccessToken() {
    return inMemoryAuthSession.accessToken ?? loadPersistedAuthSession().accessToken;
}

export function dispatchAuthExpired() {
    if (typeof window === "undefined") {
        return;
    }
    window.dispatchEvent(new CustomEvent("caps-auth-expired"));
}

function canUseLocalStorage() {
    return typeof window !== "undefined" && typeof window.localStorage !== "undefined";
}
