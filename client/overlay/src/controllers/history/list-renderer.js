import { elements } from "../../dom/elements.js";
import { getSelectedMeetingContextSummary } from "../context-controller.js";
import { appState } from "../../state/app-state.js";
import { buildEmptyState, canUseShareFeatures, isAdminUser, resolveEffectiveScope } from "./helpers.js";
import {
    buildContextSummaryText,
    buildReportMeta,
    buildSessionMeta,
    buildSharedReportMeta,
    formatReportTypeLabel,
} from "./formatters.js";

export function renderHistoryScopeControls() {
    const effectiveScope = resolveEffectiveScope();
    const canSwitchScope = appState.auth.authEnabled && isAdminUser();
    const contextSummary = getSelectedMeetingContextSummary();

    if (elements.historyScopeBadge) {
        elements.historyScopeBadge.textContent = effectiveScope === "all" ? "전체 범위" : "내 범위";
        elements.historyScopeBadge.className = `badge ${appState.history.loading ? "idle" : "live"}`;
    }

    elements.historyScopeSwitch?.classList.toggle("hidden", !canSwitchScope);

    for (const button of elements.historyScopeButtons ?? []) {
        const isActive = button.dataset.historyScope === appState.history.requestedScope;
        button.classList.toggle("active", isActive);
        button.disabled = appState.history.loading;
    }

    if (elements.historyRefreshButton) {
        elements.historyRefreshButton.disabled = appState.history.loading;
    }

    if (elements.historyContextSummary) {
        elements.historyContextSummary.textContent = contextSummary.hasSelection
            ? buildContextSummaryText(contextSummary)
            : "현재 맥락 필터 없음";
        elements.historyContextSummary.classList.toggle("is-active", contextSummary.hasSelection);
    }

    if (elements.historyContextResetButton) {
        elements.historyContextResetButton.classList.toggle("hidden", !contextSummary.hasSelection);
        elements.historyContextResetButton.disabled = appState.history.loading;
    }
}

export function renderHistoryLists() {
    renderHistoryColumn({
        container: elements.historySessionList,
        countElement: elements.historySessionCount,
        items: appState.history.sessions,
        kind: "session",
        emptyText: "아직 조회된 회의가 없습니다.",
        buildTitle: (item) => item.title || "제목 없는 회의",
        buildMeta: buildSessionMeta,
    });

    renderHistoryColumn({
        container: elements.historyReportList,
        countElement: elements.historyReportCount,
        items: appState.history.reports,
        kind: "report",
        emptyText: "아직 조회된 리포트가 없습니다.",
        buildTitle: (item) => `${formatReportTypeLabel(item.reportType)} / v${item.version}`,
        buildMeta: buildReportMeta,
    });

    const showSharedCard = canUseShareFeatures();
    elements.historySharedCard?.classList.toggle("hidden", !showSharedCard);
    if (!showSharedCard) {
        return;
    }

    renderHistoryColumn({
        container: elements.historySharedList,
        countElement: elements.historySharedCount,
        items: appState.history.sharedReports,
        kind: "shared-report",
        emptyText: "공유받은 리포트가 없습니다.",
        buildTitle: (item) => `${item.sharedByDisplayName} / ${formatReportTypeLabel(item.reportType)}`,
        buildMeta: buildSharedReportMeta,
        getItemId: (item) => item.reportId,
    });
}

function renderHistoryColumn({
    container,
    countElement,
    items,
    kind,
    emptyText,
    buildTitle,
    buildMeta,
    getItemId = (item) => item.id,
}) {
    if (!container || !countElement) {
        return;
    }

    countElement.textContent = String(items.length);
    container.replaceChildren();

    if (appState.history.loading) {
        container.append(buildEmptyState("히스토리 목록을 불러오는 중입니다."));
        return;
    }

    if (!items.length) {
        container.append(buildEmptyState(emptyText));
        return;
    }

    for (const item of items) {
        const itemId = getItemId(item);
        const button = document.createElement("button");
        button.type = "button";
        button.className = "report-history-item history-list-item";
        button.dataset.historyKind = kind;
        button.dataset.historyId = itemId;

        if (appState.history.selectedKind === kind && appState.history.selectedId === itemId) {
            button.classList.add("active");
        }

        const title = document.createElement("span");
        title.className = "history-item-title";
        title.textContent = buildTitle(item);

        const meta = document.createElement("span");
        meta.className = "history-item-meta";
        meta.textContent = buildMeta(item);

        button.append(title, meta);
        container.append(button);
    }
}
