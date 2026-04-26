import { elements } from "../../dom/elements.js";
import { fetchOverview } from "../../services/api/meeting-session-api.js";
import { normalizeOverviewPayload } from "../../services/payload-normalizers.js";
import { appState } from "../../state/app-state.js";
import { applyOverview } from "../../state/session/meeting-session-store.js";
import { finalizeSessionLocallyAfterDisconnect } from "./session-disconnect-controller.js";
import { shouldTreatAsUnexpectedSessionDisconnect } from "./session-disconnect-policy.js";

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
        if (
            appState.session.status === "running"
            && shouldTreatAsUnexpectedSessionDisconnect(error)
        ) {
            await finalizeSessionLocallyAfterDisconnect({
                reason: "서버 연결이 끊겨 현재 세션을 종료 처리했습니다.",
            });
        }
    }
}
