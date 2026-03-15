import { POLLING_INTERVAL_MS } from "../../config/constants.js";
import { appState } from "../../state/app-state.js";
import {
    clearSessionTimer,
    setSessionTimer,
} from "../../state/session/meeting-session-store.js";
import { renderEventBoard } from "../events-board-controller.js";
import { refreshSessionOverview } from "./session-overview-controller.js";

let overviewRefreshPromise = null;

export function startOverviewPolling() {
    stopOverviewPolling();
    void refreshSessionOverviewAndBoard();
    setSessionTimer(
        appState,
        window.setInterval(refreshSessionOverviewAndBoard, POLLING_INTERVAL_MS),
    );
}

export function stopOverviewPolling() {
    clearSessionTimer(appState);
}

export async function refreshSessionOverviewAndBoard() {
    if (overviewRefreshPromise) {
        return overviewRefreshPromise;
    }

    overviewRefreshPromise = (async () => {
        await refreshSessionOverview();
        renderEventBoard();
    })();

    try {
        await overviewRefreshPromise;
    } finally {
        overviewRefreshPromise = null;
    }
}
