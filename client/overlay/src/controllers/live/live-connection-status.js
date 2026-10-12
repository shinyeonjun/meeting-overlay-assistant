import { elements } from "../../dom/elements.js";
import { appState } from "../../state/app-state.js";
import { setLiveConnectionStatus } from "../../state/live-store.js";
import { setStatus } from "../ui-controller.js";

/**
 * 연결 상태 배지(텍스트 + 톤)와 상태 점(status-dot)을 갱신한다.
 */

export function updateConnectionBadge(text, tone) {
    if (!elements.liveConnectionStatus) {
        return;
    }
    setStatus(elements.liveConnectionStatus, text, tone);
}

export function syncConnectionStatus(status) {
    setLiveConnectionStatus(appState, status);
    if (elements.statusDot) {
        elements.statusDot.className = `status-dot ${status}`;
    }
}
