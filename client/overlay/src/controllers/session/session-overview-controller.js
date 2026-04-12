/** 오버레이에서 세션 흐름의 session overview controller 제어를 담당한다. */
import { elements } from "../../dom/elements.js";
import { fetchOverview } from "../../services/api/meeting-session-api.js";
import { normalizeOverviewPayload } from "../../services/payload-normalizers.js";
import { appState } from "../../state/app-state.js";
import { applyOverview } from "../../state/session/meeting-session-store.js";

export function renderCurrentTopic() {
    elements.currentTopic.textContent = appState.session.currentTopic ?? "아직 감지된 주제가 없습니다.";
}

export async function refreshSessionOverview() {
    if (!appState.session.id) {
        return;
    }

    try {
        const overviewPayload = normalizeOverviewPayload(await fetchOverview(appState.session.id));
        applyOverview(appState, overviewPayload);
        renderCurrentTopic();
    } catch (error) {
        console.error(error);
    }
}
