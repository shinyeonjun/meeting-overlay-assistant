import { TRANSCRIPT_HISTORY_LIMIT } from "../../config/constants.js";
import { normalizeStreamPayload } from "../../services/payload-normalizers.js";
import { appState } from "../../state/app-state.js";
import { applyLiveEvents, applyLiveUtterance } from "../../state/live-store.js";
import { renderEventBoard } from "../events-board-controller.js";
import { pushCompletedCaptionLine, renderCurrentUtterance } from "./live-caption-renderer.js";
import { pushEventFeed } from "./live-feed.js";

export function handlePipelinePayload(event) {
    let payload;
    try {
        let raw = JSON.parse(event.data);

        if (raw.type === "payload" && raw.payload) {
            raw = raw.payload;
        } else if (raw.type === "session") {
            return;
        }

        payload = normalizeStreamPayload(raw);
    } catch (error) {
        console.warn("[CAPS] payload 파싱 실패:", error, event.data);
        return;
    }

    if (!payload.utterances.length && !payload.events.length) {
        return;
    }

    for (const utterance of payload.utterances) {
        try {
            const completedLine = applyLiveUtterance(appState, utterance, TRANSCRIPT_HISTORY_LIMIT);
            pushCompletedCaptionLine(completedLine);
            renderCurrentUtterance();
        } catch (error) {
            console.warn("[CAPS] 발화 표시 오류:", error, utterance);
        }
    }

    try {
        applyLiveEvents(appState, payload.events);
        renderEventBoard();
        pushEventFeed("question", appState.session.overview.questions);
        pushEventFeed("decision", appState.session.overview.decisions);
        pushEventFeed("action_item", appState.session.overview.actionItems);
        pushEventFeed("risk", appState.session.overview.risks);
    } catch (error) {
        console.warn("[CAPS] 이벤트 처리 오류:", error, payload.events);
    }
}
