import {
    DEFAULT_BACKEND_PYTHON,
    DEFAULT_LIVE_AUDIO_CHANNELS,
    DEFAULT_LIVE_AUDIO_CHUNK_MS,
    DEFAULT_LIVE_AUDIO_SAMPLE_RATE,
    DEFAULT_LIVE_AUDIO_SCRIPT_PATH,
    DEFAULT_WEB_SPEECH_LANG,
} from "../../config/defaults.js";
import { elements } from "../../dom/elements.js";
import { openLiveSocket } from "../../services/live-socket.js";
import {
    createWebSpeechRecognizer,
    isWebSpeechSupported,
} from "../../services/web-speech-recognizer.js";
import {
    isTauriRuntime,
    listenTauriEvent,
    startTauriLiveAudioStream,
    stopTauriLiveAudioStream,
} from "../../services/tauri-live-audio.js";
import { appState } from "../../state/app-state.js";
import {
    clearCurrentUtterance,
    setLiveConnectionStatus,
    setLiveSocket,
} from "../../state/live-store.js";
import { wait } from "../../utils/wait.js";
import { flashStatus, setStatus } from "../ui-controller.js";
import { renderCurrentUtterance } from "./live-caption-renderer.js";
import { handlePipelinePayload } from "./live-payload-handler.js";

const MIC_SOURCE = "mic";
const FILE_SOURCE = "file";
const MIXED_SOURCE = "mic_and_audio";
const SYSTEM_AUDIO_SOURCE = "system_audio";
const TAURI_AUDIO_SOURCES = new Set([SYSTEM_AUDIO_SOURCE]);
const TAURI_BRIDGE_MAX_RETRIES = 3;
const TAURI_BRIDGE_RETRY_DELAY_MS = 1000;
const TAURI_RUNTIME_READY_MAX_RETRIES = 20;
const TAURI_RUNTIME_READY_DELAY_MS = 250;
const MIC_SOCKET_CONNECT_TIMEOUT_MS = 5000;

let tauriPayloadUnlisten = null;
let tauriLogUnlisten = null;
let tauriStreamActive = false;
let tauriBridgeReady = false;
let tauriBridgeSetupPromise = null;
let tauriBeforeUnloadBound = false;

let webSpeechRecognizer = null;
let webSpeechActive = false;
let webSpeechSeqNum = 0;
let webSpeechRevision = 0;
let webSpeechSegmentId = null;
let webSpeechLastInterim = "";
let webSpeechPendingFinalTexts = [];
let micFallbackInProgress = false;
let lastMicFinalText = "";
let lastMicFinalSentAt = 0;

function updateConnectionBadge(text, tone) {
    if (!elements.liveConnectionStatus) {
        return;
    }
    setStatus(elements.liveConnectionStatus, text, tone);
}

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

function syncConnectionStatus(status) {
    setLiveConnectionStatus(appState, status);
    if (elements.statusDot) {
        elements.statusDot.className = `status-dot ${status}`;
    }
}

function connectTextInputWebSocket({
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

async function connectTauriLiveAudio(source) {
    const bridgeReady = await setupTauriLiveAudioBridge();
    if (!bridgeReady) {
        throw new Error("Tauri live audio bridge 초기화에 실패했습니다.");
    }

    syncConnectionStatus("live");
    updateConnectionBadge("오디오 연결 중", "live");

    await startTauriLiveAudioStream({
        pythonExe: DEFAULT_BACKEND_PYTHON,
        scriptPath: DEFAULT_LIVE_AUDIO_SCRIPT_PATH,
        sessionId: appState.session.id,
        source,
        sampleRate: DEFAULT_LIVE_AUDIO_SAMPLE_RATE,
        channels: DEFAULT_LIVE_AUDIO_CHANNELS,
        chunkMs: DEFAULT_LIVE_AUDIO_CHUNK_MS,
    });

    tauriStreamActive = true;
    updateConnectionBadge("오디오 스트림 활성", "live");
}

function emitWebSpeechPartial(text) {
    const normalized = text.trim();
    if (!normalized || normalized === webSpeechLastInterim || !appState.session.id) {
        return;
    }

    if (webSpeechSegmentId === null) {
        webSpeechSeqNum += 1;
        webSpeechRevision = 0;
        webSpeechSegmentId = `seg-webspeech-${webSpeechSeqNum}`;
    }

    webSpeechRevision += 1;
    webSpeechLastInterim = normalized;
    const nowMs = Date.now();
    const payload = {
        type: "payload",
        payload: {
            session_id: appState.session.id,
            utterances: [
                {
                    id: `live-webspeech-${webSpeechSeqNum}-${webSpeechRevision}`,
                    seq_num: webSpeechSeqNum,
                    segment_id: webSpeechSegmentId,
                    text: normalized,
                    confidence: 0.7,
                    start_ms: nowMs,
                    end_ms: nowMs,
                    is_partial: true,
                    kind: "partial",
                    revision: webSpeechRevision,
                    input_source: MIC_SOURCE,
                },
            ],
            events: [],
            error: null,
        },
    };

    handlePipelinePayload({ data: JSON.stringify(payload) });
}

function queueWebSpeechFinal(text) {
    const normalized = text.trim();
    if (!normalized) {
        return;
    }

    const now = Date.now();
    if (normalized === lastMicFinalText && now - lastMicFinalSentAt < 1000) {
        return;
    }

    lastMicFinalText = normalized;
    lastMicFinalSentAt = now;
    webSpeechPendingFinalTexts.push(normalized);
    webSpeechSegmentId = null;
    webSpeechRevision = 0;
    webSpeechLastInterim = "";
    flushWebSpeechFinalQueue();
}

function flushWebSpeechFinalQueue() {
    const socket = appState.live.socket;
    if (!socket || socket.readyState !== WebSocket.OPEN) {
        return;
    }

    while (webSpeechPendingFinalTexts.length > 0) {
        const line = webSpeechPendingFinalTexts.shift();
        if (line) {
            socket.send(line);
        }
    }
}

function stopWebSpeechRecognizer() {
    if (webSpeechRecognizer) {
        webSpeechRecognizer.stop();
    }
    webSpeechRecognizer = null;
    webSpeechActive = false;
    webSpeechSegmentId = null;
    webSpeechRevision = 0;
    webSpeechLastInterim = "";
    webSpeechPendingFinalTexts = [];
}

async function activateMicFallback(reason) {
    if (micFallbackInProgress) {
        return;
    }

    micFallbackInProgress = true;
    try {
        console.warn("[CAPS] mic Web Speech fallback 활성화", reason);
        const currentSource = appState.session.source ?? elements.sessionSource.value;
        if (currentSource === MIXED_SOURCE) {
            updateConnectionBadge("mic(Web Speech) 비활성, system_audio 유지", "idle");
            return;
        }

        stopWebSpeechRecognizer();
        if (appState.live.socket) {
            appState.live.socket.close();
            setLiveSocket(appState, null);
        }

        updateConnectionBadge("mic fallback 연결 중", "idle");
        await connectTauriLiveAudio(MIC_SOURCE);
    } catch (error) {
        console.error("[CAPS] mic fallback 실패:", error);
        syncConnectionStatus("error");
        updateConnectionBadge("mic fallback 실패", "error");
    } finally {
        micFallbackInProgress = false;
    }
}

function startWebSpeechRecognizer() {
    if (!isWebSpeechSupported()) {
        throw new Error("Web Speech API를 지원하지 않는 환경입니다.");
    }

    webSpeechRecognizer = createWebSpeechRecognizer({
        lang: DEFAULT_WEB_SPEECH_LANG,
        interimResults: true,
        continuous: true,
        onInterim: (text) => {
            emitWebSpeechPartial(text);
        },
        onFinal: (text) => {
            queueWebSpeechFinal(text);
        },
        onStart: () => {
            webSpeechActive = true;
            updateConnectionBadge("mic 입력: 브라우저 기본 마이크", "live");
        },
        onEnd: () => {
            if (!webSpeechActive) {
                return;
            }
            updateConnectionBadge("mic(Web Speech) 재시작 중", "idle");
        },
        onError: (error, meta) => {
            console.warn("[CAPS] Web Speech 오류:", error, meta);
            if (meta?.fatal) {
                void activateMicFallback(meta.code ?? "fatal_error");
                return;
            }
            updateConnectionBadge("mic(Web Speech) 오류", "error");
        },
    });
    webSpeechRecognizer.start();
}

async function connectMicViaWebSpeech() {
    if (!isWebSpeechSupported()) {
        throw new Error("Web Speech API 미지원");
    }

    stopWebSpeechRecognizer();
    webSpeechSeqNum = 0;
    webSpeechRevision = 0;
    webSpeechSegmentId = null;
    webSpeechLastInterim = "";
    webSpeechPendingFinalTexts = [];

    await new Promise((resolve, reject) => {
        let settled = false;
        const timeoutId = window.setTimeout(() => {
            if (settled) {
                return;
            }
            settled = true;
            reject(new Error("mic text-input WebSocket 연결 타임아웃"));
        }, MIC_SOCKET_CONNECT_TIMEOUT_MS);

        connectTextInputWebSocket({
            onOpen: () => {
                if (settled) {
                    return;
                }
                try {
                    startWebSpeechRecognizer();
                    flushWebSpeechFinalQueue();
                    settled = true;
                    window.clearTimeout(timeoutId);
                    resolve();
                } catch (error) {
                    settled = true;
                    window.clearTimeout(timeoutId);
                    reject(error);
                }
            },
            onClose: () => {
                if (webSpeechActive) {
                    stopWebSpeechRecognizer();
                }
                if (!settled) {
                    settled = true;
                    window.clearTimeout(timeoutId);
                    reject(new Error("mic text-input WebSocket 연결이 닫혔습니다."));
                    return;
                }
                updateConnectionBadge("대기", "idle");
            },
            onError: () => {
                if (settled) {
                    updateConnectionBadge("오류", "error");
                    return;
                }
                settled = true;
                window.clearTimeout(timeoutId);
                reject(new Error("mic text-input WebSocket 연결 오류"));
            },
        });
    });
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

export async function connectLiveSource() {
    if (!appState.session.id) {
        flashStatus(elements.liveConnectionStatus, "세션 필요", "error");
        return;
    }

    const source = appState.session.source ?? elements.sessionSource.value;

    try {
        await stopActiveLiveConnection();

        if (source === FILE_SOURCE) {
            updateConnectionBadge("파일 모드는 실시간 연결이 없습니다.", "idle");
            return;
        }

        if (!isTauriRuntime() && source === SYSTEM_AUDIO_SOURCE) {
            flashStatus(elements.liveConnectionStatus, "system_audio는 Tauri 앱에서만 지원됩니다.", "error");
            return;
        }

        if (source === MIC_SOURCE) {
            try {
                await connectMicViaWebSpeech();
                return;
            } catch (error) {
                console.warn("[CAPS] mic Web Speech 연결 실패. backend STT로 fallback:", error);
                await connectTauriLiveAudio(MIC_SOURCE);
                return;
            }
        }

        if (source === MIXED_SOURCE) {
            if (!isTauriRuntime()) {
                await connectMicViaWebSpeech();
                updateConnectionBadge("브라우저 모드: mic만 활성", "live");
                return;
            }

            try {
                await connectMicViaWebSpeech();
            } catch (error) {
                console.warn("[CAPS] mic_and_audio 모드: mic Web Speech 시작 실패, system_audio만 유지:", error);
            }
            await connectTauriLiveAudio(SYSTEM_AUDIO_SOURCE);
            return;
        }

        if (TAURI_AUDIO_SOURCES.has(source)) {
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

export async function stopActiveLiveConnection() {
    stopWebSpeechRecognizer();

    if (appState.live.socket) {
        appState.live.socket.close();
        setLiveSocket(appState, null);
    }

    if (tauriStreamActive) {
        await stopTauriLiveAudioStream();
        tauriStreamActive = false;
    }

    clearCurrentUtterance(appState);
    renderCurrentUtterance();
    syncConnectionStatus("idle");
    updateConnectionBadge("대기", "idle");
}
