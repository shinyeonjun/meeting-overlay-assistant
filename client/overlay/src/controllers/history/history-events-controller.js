import { elements } from "../../dom/elements.js";
import { appState } from "../../state/app-state.js";
import {
    selectHistoryItem,
    setHistoryRequestedScope,
} from "../../state/history-store.js";
import {
    handleCreateShare,
    refreshSelectedHistoryDetails,
} from "./detail-share-controller.js";
import { renderHistoryBoard } from "./history-render-controller.js";
import {
    handleHistoryContextReset,
    refreshHistoryBoard,
} from "./history-refresh-controller.js";

let historyEventsBound = false;

export function setupHistoryControls() {
    if (historyEventsBound) {
        return;
    }

    elements.historyRefreshButton?.addEventListener("click", () => {
        void refreshHistoryBoard();
    });
    elements.historyContextResetButton?.addEventListener("click", handleHistoryContextReset);

    for (const button of elements.historyScopeButtons ?? []) {
        button.addEventListener("click", () => {
            const nextScope = button.dataset.historyScope;
            if (!nextScope || nextScope === appState.history.requestedScope) {
                return;
            }
            setHistoryRequestedScope(appState, nextScope);
            renderHistoryBoard();
            void refreshHistoryBoard();
        });
    }

    elements.historySessionList?.addEventListener("click", (event) => {
        const button = event.target.closest("[data-history-kind='session']");
        if (!button) {
            return;
        }
        selectHistoryItem(appState, "session", button.dataset.historyId);
        renderHistoryBoard();
    });

    elements.historyReportList?.addEventListener("click", (event) => {
        const button = event.target.closest("[data-history-kind='report']");
        if (!button) {
            return;
        }
        selectHistoryItem(appState, "report", button.dataset.historyId);
        renderHistoryBoard();
        void refreshSelectedHistoryDetails();
    });

    elements.historySharedList?.addEventListener("click", (event) => {
        const button = event.target.closest("[data-history-kind='shared-report']");
        if (!button) {
            return;
        }
        selectHistoryItem(appState, "shared-report", button.dataset.historyId);
        renderHistoryBoard();
        void refreshSelectedHistoryDetails();
    });

    elements.historyTimelineList?.addEventListener("click", (event) => {
        const button = event.target.closest("[data-history-kind][data-history-id]");
        if (!button) {
            return;
        }

        const nextKind = button.dataset.historyKind;
        const nextId = button.dataset.historyId;
        if (!nextKind || !nextId) {
            return;
        }

        selectHistoryItem(appState, nextKind, nextId);
        renderHistoryBoard();

        if (nextKind === "report" || nextKind === "shared-report") {
            void refreshSelectedHistoryDetails();
        }
    });

    elements.historyShareButton?.addEventListener("click", () => {
        void handleCreateShare();
    });

    historyEventsBound = true;
}
