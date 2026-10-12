import { openLiveSocket } from "../../services/live-socket.js";
import { appState } from "../../state/app-state.js";
import { setLiveSocket } from "../../state/live-store.js";
import { handlePipelinePayload } from "./live-payload-handler.js";
import { syncConnectionStatus } from "./live-connection-status.js";

/**
 * 텍스트 입력용 라이브 WebSocket 연결 생성과 상태 동기화.
 */

export function connectTextInputWebSocket({
    onOpen,
    onClose,
    onError,
    onMessage,
} = {}) {
    const socket = openLiveSocket(appState.session.id, "text_input", {
        onOpen: () => {
            syncConnectionStatus("live");
            onOpen?.(socket);
        },
        onClose: () => {
            setLiveSocket(appState, null);
            syncConnectionStatus("idle");
            onClose?.(socket);
        },
        onError: () => {
            syncConnectionStatus("error");
            onError?.(socket);
        },
        onMessage: onMessage ?? handlePipelinePayload,
    });

    setLiveSocket(appState, socket);
    return socket;
}
