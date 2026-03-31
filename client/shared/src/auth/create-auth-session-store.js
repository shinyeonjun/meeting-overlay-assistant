export function createAuthSessionStore({
    storageKey,
    expiredEventName = "caps-auth-expired",
}) {
    let inMemoryAuthSession = {
        accessToken: null,
        user: null,
    };

    function loadPersistedAuthSession() {
        if (!canUseLocalStorage()) {
            return emptyPersistedSession();
        }

        try {
            const rawValue = window.localStorage.getItem(storageKey);
            if (!rawValue) {
                inMemoryAuthSession = emptyInMemorySession();
                return emptyPersistedSession();
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
            inMemoryAuthSession = emptyInMemorySession();
            return emptyPersistedSession();
        }
    }

    function persistAuthSession({ accessToken, user, autoLoginEnabled = true }) {
        inMemoryAuthSession = {
            accessToken,
            user,
        };

        if (!canUseLocalStorage()) {
            return;
        }

        window.localStorage.setItem(
            storageKey,
            JSON.stringify({
                accessToken: autoLoginEnabled ? accessToken : null,
                user: autoLoginEnabled ? user : null,
                autoLoginEnabled,
            }),
        );
    }

    function clearPersistedAuthSession() {
        inMemoryAuthSession = emptyInMemorySession();
        if (!canUseLocalStorage()) {
            return;
        }
        window.localStorage.removeItem(storageKey);
    }

    function getPersistedAccessToken() {
        return inMemoryAuthSession.accessToken ?? loadPersistedAuthSession().accessToken;
    }

    function dispatchAuthExpired() {
        if (typeof window === "undefined") {
            return;
        }
        window.dispatchEvent(new CustomEvent(expiredEventName));
    }

    return {
        clearPersistedAuthSession,
        dispatchAuthExpired,
        getPersistedAccessToken,
        loadPersistedAuthSession,
        persistAuthSession,
    };
}

function canUseLocalStorage() {
    return typeof window !== "undefined" && typeof window.localStorage !== "undefined";
}

function emptyInMemorySession() {
    return {
        accessToken: null,
        user: null,
    };
}

function emptyPersistedSession() {
    return {
        accessToken: null,
        user: null,
        autoLoginEnabled: true,
    };
}
