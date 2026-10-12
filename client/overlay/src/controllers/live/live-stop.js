import { stopTauriLiveAudioStream } from "../../services/tauri-live-audio.js";
import { appState } from "../../state/app-state.js";
import { clearCurrentUtterance, setLiveSocket } from "../../state/live-store.js";
import { renderCurrentUtterance } from "./live-caption-renderer.js";
import { syncConnectionStatus, updateConnectionBadge } from "./live-connection-status.js";
import { tauriAudioState } from "./live-tauri-audio-state.js";

/**
 * 활성 라이브 연결(WebSocket, Tauri 오디오 스트림)을 정리하고 대기 상태로 되돌린다.
 */

export async function stopActiveLiveConnection({ preservePrewarmedSource = null } = {}) {
    if (appState.live.socket) {
        appState.live.socket.close();
        setLiveSocket(appState, null);
    }

    const shouldKeepPrewarmed = (
        !tauriAudioState.streamActive
        && preservePrewarmedSource
        && tauriAudioState.prewarmedSource === preservePrewarmedSource
    );

    if ((tauriAudioState.streamActive || tauriAudioState.prewarmedSource) && !shouldKeepPrewarmed) {
        await stopTauriLiveAudioStream();
        tauriAudioState.streamActive = false;
        tauriAudioState.prewarmedSource = null;
    }

    clearCurrentUtterance(appState);
    renderCurrentUtterance();
    syncConnectionStatus("idle");
    updateConnectionBadge("대기", "idle");
}
