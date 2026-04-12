/** 오버레이에서 세션 흐름의 session timer 제어를 담당한다. */
import { appState } from "../../state/app-state.js";

let elapsedTimerId = null;

export function startElapsedTimer() {
    stopElapsedTimer();

    const timerEl = document.querySelector("#session-elapsed");
    if (!timerEl) {
        return;
    }

    const startTime = Date.parse(appState.session.startedAt ?? "") || Date.now();

    const tick = () => {
        const elapsed = Math.max(0, Math.floor((Date.now() - startTime) / 1000));
        const minutes = String(Math.floor(elapsed / 60)).padStart(2, "0");
        const seconds = String(elapsed % 60).padStart(2, "0");
        timerEl.textContent = `${minutes}:${seconds}`;
    };

    tick();
    elapsedTimerId = window.setInterval(tick, 1000);
}

export function stopElapsedTimer() {
    if (elapsedTimerId !== null) {
        window.clearInterval(elapsedTimerId);
        elapsedTimerId = null;
    }
}
