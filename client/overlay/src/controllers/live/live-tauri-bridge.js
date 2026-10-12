import {
    isTauriRuntime,
    listenTauriEvent,
} from "../../services/tauri-live-audio.js";
import { wait } from "../../utils/wait.js";
import { handlePipelinePayload } from "./live-payload-handler.js";
import { updateConnectionBadge } from "./live-connection-status.js";
import { stopActiveLiveConnection } from "./live-stop.js";

/**
 * Tauri 이벤트 브리지(live-audio-payload / live-audio-log) 초기화와 payload 라우팅.
 */

const TAURI_BRIDGE_MAX_RETRIES = 3;
const TAURI_BRIDGE_RETRY_DELAY_MS = 1000;
const TAURI_RUNTIME_READY_MAX_RETRIES = 20;
const TAURI_RUNTIME_READY_DELAY_MS = 250;

let tauriPayloadUnlisten = null;
let tauriLogUnlisten = null;
let tauriBridgeReady = false;
let tauriBridgeSetupPromise = null;
let tauriBeforeUnloadBound = false;

function handleCaptureInfoPayload(rawPayload) {
    if (rawPayload?.type !== "capture_info") {
        return false;
    }

    const source = rawPayload.source ?? "unknown";
    const deviceName = rawPayload.device_name ?? "unknown";
    updateConnectionBadge(`${source} 입력: ${deviceName}`, "live");
    return true;
}

function routeTauriPayloadLine(payloadLine) {
    try {
        const parsed = JSON.parse(payloadLine);
        if (handleCaptureInfoPayload(parsed)) {
            return;
        }
    } catch {
        // payload 문자열이면 기존 파이프라인 처리로 넘긴다.
    }

    handlePipelinePayload({ data: payloadLine });
}

async function ensureTauriRuntimeReady() {
    for (let attempt = 1; attempt <= TAURI_RUNTIME_READY_MAX_RETRIES; attempt += 1) {
        if (isTauriRuntime()) {
            return true;
        }
        await wait(TAURI_RUNTIME_READY_DELAY_MS);
    }
    return false;
}

async function ensureTauriLiveAudioBridgeReady() {
    if (tauriBridgeReady) {
        return true;
    }

    if (tauriBridgeSetupPromise) {
        return tauriBridgeSetupPromise;
    }

    tauriBridgeSetupPromise = (async () => {
        const runtimeReady = await ensureTauriRuntimeReady();
        if (!runtimeReady) {
            console.info("[CAPS] 브라우저 개발 모드 또는 Tauri runtime 미준비: live audio bridge 비활성화");
            return false;
        }

        if (tauriPayloadUnlisten && tauriLogUnlisten) {
            tauriBridgeReady = true;
            return true;
        }

        for (let attempt = 1; attempt <= TAURI_BRIDGE_MAX_RETRIES; attempt += 1) {
            try {
                tauriPayloadUnlisten = await listenTauriEvent("live-audio-payload", (event) => {
                    routeTauriPayloadLine(event.payload);
                });
                tauriLogUnlisten = await listenTauriEvent("live-audio-log", (event) => {
                    console.error(event.payload?.message ?? event.payload);
                });
                tauriBridgeReady = true;
                console.info(`[CAPS] Tauri live audio bridge 초기화 성공 (${attempt}/${TAURI_BRIDGE_MAX_RETRIES})`);
                break;
            } catch (error) {
                console.warn(`[CAPS] Tauri bridge 초기화 실패 (${attempt}/${TAURI_BRIDGE_MAX_RETRIES}):`, error);
                if (attempt === TAURI_BRIDGE_MAX_RETRIES) {
                    console.error("[CAPS] Tauri bridge 최대 재시도 초과");
                    return false;
                }
                await wait(TAURI_BRIDGE_RETRY_DELAY_MS);
            }
        }

        if (!tauriBeforeUnloadBound) {
            tauriBeforeUnloadBound = true;
            window.addEventListener("beforeunload", () => {
                void stopActiveLiveConnection();
                tauriPayloadUnlisten?.();
                tauriLogUnlisten?.();
                tauriPayloadUnlisten = null;
                tauriLogUnlisten = null;
                tauriBridgeReady = false;
            });
        }

        return tauriBridgeReady;
    })();

    try {
        return await tauriBridgeSetupPromise;
    } finally {
        tauriBridgeSetupPromise = null;
    }
}

export async function setupTauriLiveAudioBridge() {
    return ensureTauriLiveAudioBridgeReady();
}
