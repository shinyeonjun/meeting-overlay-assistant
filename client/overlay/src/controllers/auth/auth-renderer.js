/** 오버레이에서 인증 흐름의 auth renderer 제어를 담당한다. */
import {
    getApiBaseUrl,
    getLiveApiBaseUrl,
    setApiBaseUrl,
    setLiveApiBaseUrl,
} from "../../config/runtime.js";
import { elements } from "../../dom/elements.js";
import { appState } from "../../state/app-state.js";
import { setAuthServerUrls } from "../../state/auth-store.js";
import { renderWorkflowSummary } from "../ui/workflow-summary-controller.js";

export function applyServerUrls() {
    const nextServerUrl = setApiBaseUrl(
        elements.serverUrlInput?.value || getApiBaseUrl(),
    );
    const nextLiveServerUrl = setLiveApiBaseUrl(
        elements.liveServerUrlInput?.value || getLiveApiBaseUrl(),
    );
    setAuthServerUrls(appState, {
        serverUrl: nextServerUrl,
        liveServerUrl: nextLiveServerUrl,
    });
    if (elements.serverUrlInput) {
        elements.serverUrlInput.value = nextServerUrl;
    }
    if (elements.liveServerUrlInput) {
        elements.liveServerUrlInput.value = nextLiveServerUrl;
    }
    updateBootstrapCommand(nextServerUrl);
    return {
        serverUrl: nextServerUrl,
        liveServerUrl: nextLiveServerUrl,
    };
}

export function renderHeaderSummary() {
    if (!elements.authUserSummary || !elements.logoutButton) {
        return;
    }

    if (appState.auth.user) {
        const roleLabel = appState.auth.user.workspace_role ?? "member";
        elements.authUserSummary.textContent =
            `${appState.auth.user.display_name} | ${roleLabel}`;
        elements.authUserSummary.classList.remove("hidden");
        elements.logoutButton.classList.remove("hidden");
        renderWorkflowSummary();
        return;
    }

    elements.authUserSummary.textContent = "";
    elements.authUserSummary.classList.add("hidden");
    elements.logoutButton.classList.add("hidden");
    renderWorkflowSummary();
}

export function setAuthStatusText(text) {
    if (elements.authStatusText) {
        elements.authStatusText.textContent = text;
    }
    renderWorkflowSummary();
}

export function renderAutoLoginChoice() {
    if (!elements.authRememberCheckbox) {
        return;
    }
    elements.authRememberCheckbox.checked = appState.auth.autoLoginEnabled !== false;
}

export function toggleBootstrapNote(visible) {
    elements.authBootstrapNote?.classList.toggle("hidden", !visible);
}

export function toggleLoginForm(visible) {
    elements.authLoginForm?.classList.toggle("hidden", !visible);
}

export function showAuthGate() {
    elements.authGate?.classList.remove("hidden");
}

export function hideAuthGate() {
    elements.authGate?.classList.add("hidden");
}

function updateBootstrapCommand(serverUrl) {
    if (!elements.authBootstrapCommand) {
        return;
    }
    elements.authBootstrapCommand.textContent = [
        "powershell -ExecutionPolicy Bypass -File .\\scripts\\server-admin.ps1 bootstrap-admin",
        "--login-id owner",
        '--display-name "관리자"',
        `# target=${serverUrl}`,
    ].join(" ");
}
