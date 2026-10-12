import {
    AUDIO_SOURCE,
    LIVE_CONNECTION_MODE,
    resolveLiveConnectionMode,
} from "../../audio/source-policy.js";
import { elements } from "../../dom/elements.js";
import { isTauriRuntime } from "../../services/tauri-live-audio.js";
import { appState } from "../../state/app-state.js";
import { flashStatus } from "../ui-controller.js";
import { syncConnectionStatus, updateConnectionBadge } from "./live-connection-status.js";
import { stopActiveLiveConnection } from "./live-stop.js";
import {
    connectTauriLiveAudio,
    ensureTauriLiveAudioPrewarmed,
    resolveTauriPrewarmSource,
} from "./live-tauri-audio.js";
import { setupTauriLiveAudioBridge } from "./live-tauri-bridge.js";
import { connectTextInputWebSocket } from "./live-text-websocket.js";

/**
 * 라이브 연결 진입점. 연결 모드를 판단해 Tauri 오디오 또는 텍스트 WebSocket 경로로 분기한다.
 * 역할별 구현은 같은 폴더의 모듈에 있고, 기존 import 경로를 위해 여기서 다시 내보낸다.
 */

const LOCAL_MIC_UNSUPPORTED_MESSAGE = "로컬 STT 마이크는 Tauri 앱에서만 지원됩니다.";

export async function connectLiveSource() {
    if (!appState.session.id) {
        flashStatus(elements.liveConnectionStatus, "세션 필요", "error");
        return;
    }

    const source = appState.session.primaryInputSource ?? elements.sessionSource.value;
    const connectionMode = resolveLiveConnectionMode(source, isTauriRuntime());
    const prewarmSource = resolveTauriPrewarmSource(source);

    try {
        await stopActiveLiveConnection({ preservePrewarmedSource: prewarmSource });

        if (connectionMode === LIVE_CONNECTION_MODE.FILE_IDLE) {
            updateConnectionBadge("파일 모드는 실시간 연결이 없습니다.", "idle");
            return;
        }

        if (connectionMode === LIVE_CONNECTION_MODE.SYSTEM_AUDIO_UNSUPPORTED) {
            flashStatus(elements.liveConnectionStatus, "system_audio는 Tauri 앱에서만 지원됩니다.", "error");
            return;
        }

        if (connectionMode === LIVE_CONNECTION_MODE.MIC_LOCAL_TAURI) {
            await connectTauriLiveAudio(AUDIO_SOURCE.MIC);
            return;
        }

        if (
            connectionMode === LIVE_CONNECTION_MODE.MIC_LOCAL_UNSUPPORTED
            || connectionMode === LIVE_CONNECTION_MODE.MIXED_LOCAL_UNSUPPORTED
        ) {
            flashStatus(elements.liveConnectionStatus, LOCAL_MIC_UNSUPPORTED_MESSAGE, "error");
            return;
        }

        if (connectionMode === LIVE_CONNECTION_MODE.MIXED_LOCAL_TAURI) {
            await connectTauriLiveAudio(AUDIO_SOURCE.MIXED);
            return;
        }

        if (connectionMode === LIVE_CONNECTION_MODE.SYSTEM_AUDIO_TAURI) {
            await connectTauriLiveAudio(source);
            return;
        }

        connectTextInputWebSocket({
            onOpen: () => updateConnectionBadge("연결됨", "live"),
            onClose: () => updateConnectionBadge("대기", "idle"),
            onError: () => updateConnectionBadge("오류", "error"),
        });
    } catch (error) {
        console.error(error);
        syncConnectionStatus("error");
        updateConnectionBadge("연결 실패", "error");
    }
}

export { ensureTauriLiveAudioPrewarmed, setupTauriLiveAudioBridge, stopActiveLiveConnection };
