import { elements } from "../../dom/elements.js";
import {
    fetchAuthConfig,
    fetchCurrentUser,
    login,
    logout,
} from "../../services/api/auth-api.js";
import { appState } from "../../state/app-state.js";
import {
    applyAuthConfig,
    clearAuthenticatedSession,
    isAuthenticated,
    setAutoLoginEnabled,
    setAuthenticatedSession,
} from "../../state/auth-store.js";
import { resetMeetingContextControls } from "../context-controller.js";
import { stopActiveLiveConnection } from "../live-controller.js";
import { closeWorkspace, setStatus } from "../ui-controller.js";
import {
    applyServerUrls,
    hideAuthGate,
    renderAutoLoginChoice,
    renderHeaderSummary,
    setAuthStatusText,
    showAuthGate,
    toggleBootstrapNote,
    toggleLoginForm,
} from "./auth-renderer.js";

let authReadyCallback = null;

export function setAuthReadyCallback(callback) {
    authReadyCallback = callback;
}

export async function refreshAuthState({ preferStoredSession = false } = {}) {
    const previousServerUrl = appState.auth.serverUrl;
    const previousLiveServerUrl = appState.auth.liveServerUrl;
    const {
        serverUrl: nextServerUrl,
        liveServerUrl: nextLiveServerUrl,
    } = applyServerUrls();
    if (
        (
            (previousServerUrl && previousServerUrl !== nextServerUrl)
            || (previousLiveServerUrl && previousLiveServerUrl !== nextLiveServerUrl)
        )
        && appState.auth.accessToken
    ) {
        clearAuthenticatedSession(appState);
    }

    showAuthGate();
    setStatus(elements.authModeBadge, "checking", "idle");
    setStatus(elements.authServerBadge, "probing", "idle");
    setAuthStatusText("서버 인증 설정을 확인하는 중입니다.");
    toggleBootstrapNote(false);
    toggleLoginForm(false);
    renderAutoLoginChoice();

    try {
        const authConfig = await fetchAuthConfig();
        applyAuthConfig(appState, authConfig);
        renderHeaderSummary();

        if (!appState.auth.authEnabled) {
            setAuthStatusText("이 서버는 로그인 없이 사용할 수 있습니다.");
            completeAuthenticatedExperience();
            return true;
        }

        setStatus(elements.authServerBadge, "online", "live");

        if (appState.auth.bootstrapRequired) {
            clearAuthenticatedSession(appState);
            renderHeaderSummary();
            setStatus(elements.authModeBadge, "bootstrap", "idle");
            setAuthStatusText("서버 초기 관리자 계정을 먼저 생성해야 합니다.");
            toggleBootstrapNote(true);
            toggleLoginForm(false);
            renderAutoLoginChoice();
            return false;
        }

        toggleBootstrapNote(false);
        if (preferStoredSession && isAuthenticated(appState)) {
            const resumed = await tryResumeStoredSession();
            if (resumed) {
                return true;
            }
        }

        setStatus(elements.authModeBadge, "login", "live");
        setAuthStatusText("이 서버는 로그인이 필요합니다.");
        toggleLoginForm(true);
        renderAutoLoginChoice();
        showAuthGate();
        return false;
    } catch (error) {
        console.error("[CAPS] auth config 조회 실패:", error);
        setStatus(elements.authModeBadge, "blocked", "error");
        setStatus(elements.authServerBadge, "offline", "error");
        toggleBootstrapNote(false);
        toggleLoginForm(false);
        renderAutoLoginChoice();
        setAuthStatusText(
            "서버에 연결하지 못했습니다. 주소를 확인하고 다시 시도해 주세요.",
        );
        showAuthGate();
        return false;
    }
}

export async function handleLoginSubmit(event) {
    event.preventDefault();

    const loginId = elements.authLoginId?.value.trim();
    const password = elements.authPassword?.value ?? "";
    const autoLoginEnabled = elements.authRememberCheckbox?.checked !== false;

    if (!loginId || !password) {
        setAuthStatusText("로그인 아이디와 비밀번호를 모두 입력해 주세요.");
        setStatus(elements.authModeBadge, "login", "error");
        return;
    }

    elements.authLoginButton.disabled = true;
    setAutoLoginEnabled(appState, autoLoginEnabled);
    setStatus(elements.authModeBadge, "auth", "idle");
    setStatus(elements.authServerBadge, "online", "live");
    setAuthStatusText("로그인 중입니다.");

    try {
        const payload = await login({
            loginId,
            password,
            clientType: "desktop",
        });
        setAuthenticatedSession(appState, {
            accessToken: payload.access_token,
            user: payload.user,
        });
        renderHeaderSummary();
        elements.authPassword.value = "";
        completeAuthenticatedExperience();
    } catch (error) {
        console.error("[CAPS] 로그인 실패:", error);
        setStatus(elements.authModeBadge, "login", "error");
        setStatus(elements.authServerBadge, "online", "live");
        setAuthStatusText(
            "로그인에 실패했습니다. 계정 정보와 서버 설정을 확인해 주세요.",
        );
        showAuthGate();
    } finally {
        elements.authLoginButton.disabled = false;
    }
}

export async function handleLogout() {
    elements.logoutButton.disabled = true;
    try {
        if (appState.auth.accessToken) {
            await logout();
        }
    } catch (error) {
        console.warn("[CAPS] 로그아웃 API 호출 실패:", error);
    } finally {
        elements.logoutButton.disabled = false;
    }

    await stopActiveLiveConnection();
    clearAuthenticatedSession(appState);
    resetMeetingContextControls();
    renderHeaderSummary();
    closeWorkspace();
    await refreshAuthState({ preferStoredSession: false });
}

export async function handleAuthExpired() {
    await stopActiveLiveConnection();
    clearAuthenticatedSession(appState);
    resetMeetingContextControls();
    renderHeaderSummary();
    closeWorkspace();
    setAuthStatusText("세션이 만료됐거나 인증이 해제됐습니다. 다시 로그인해 주세요.");
    await refreshAuthState({ preferStoredSession: false });
}

async function tryResumeStoredSession() {
    setStatus(elements.authModeBadge, "resume", "idle");
    setAuthStatusText("저장된 로그인 상태를 확인하는 중입니다.");

    try {
        const user = await fetchCurrentUser();
        setAuthenticatedSession(appState, {
            accessToken: appState.auth.accessToken,
            user,
        });
        renderHeaderSummary();
        completeAuthenticatedExperience();
        return true;
    } catch (error) {
        console.warn("[CAPS] 저장된 세션 복구 실패:", error);
        clearAuthenticatedSession(appState);
        renderHeaderSummary();
        setStatus(elements.authModeBadge, "login", "live");
        setAuthStatusText("저장된 로그인 정보가 만료되어 다시 로그인해야 합니다.");
        toggleLoginForm(true);
        renderAutoLoginChoice();
        showAuthGate();
        return false;
    }
}

function completeAuthenticatedExperience() {
    hideAuthGate();
    renderHeaderSummary();
    authReadyCallback?.();
}
