import { appState } from "../../state/app-state.js";
import { findSelectedHistoryItem } from "../../state/history-store.js";

const ADMIN_ROLES = new Set(["owner", "admin"]);

export const TIMELINE_LIMIT = 6;

export function buildEmptyState(text) {
    const element = document.createElement("div");
    element.className = "event-empty";
    element.textContent = text;
    return element;
}

export function isAdminUser() {
    const currentRole = appState.auth.user?.workspace_role;
    return ADMIN_ROLES.has(currentRole);
}

export function canUseShareFeatures() {
    return appState.auth.authEnabled && Boolean(appState.auth.user);
}

export function resolveEffectiveScope() {
    if (!appState.auth.authEnabled) {
        return "all";
    }
    if (isAdminUser()) {
        return appState.history.requestedScope;
    }
    return "mine";
}

export function resolveSelectedHistoryItem() {
    const selected = findSelectedHistoryItem(appState);
    if (selected) {
        return selected;
    }

    if (appState.history.selectedKind === "session") {
        return appState.history.timeline.sessions.find((item) => item.id === appState.history.selectedId) ?? null;
    }

    if (appState.history.selectedKind === "report") {
        return appState.history.timeline.reports.find((item) => item.id === appState.history.selectedId) ?? null;
    }

    return null;
}

export function getSelectedOwnReport() {
    const selectedItem = resolveSelectedHistoryItem();
    if (!selectedItem || appState.history.selectedKind !== "report") {
        return null;
    }
    return selectedItem;
}
