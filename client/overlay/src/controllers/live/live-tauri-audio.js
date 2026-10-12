import {
    DEFAULT_BACKEND_PYTHON,
    DEFAULT_LIVE_AUDIO_CHANNELS,
    DEFAULT_LIVE_AUDIO_CHUNK_MS,
    DEFAULT_LIVE_AUDIO_SAMPLE_RATE,
    DEFAULT_LIVE_AUDIO_SCRIPT_PATH,
} from "../../config/defaults.js";
import {
    AUDIO_SOURCE,
    LIVE_CONNECTION_MODE,
    resolveLiveConnectionMode,
} from "../../audio/source-policy.js";
import { resolveLocalCaptureProfile } from "../../audio/capture-profile.js";
import {
    isTauriRuntime,
    prewarmTauriLiveAudioStream,
    startTauriLiveAudioStream,
} from "../../services/tauri-live-audio.js";
import { appState } from "../../state/app-state.js";
import { setupTauriLiveAudioBridge } from "./live-tauri-bridge.js";
import { syncConnectionStatus, updateConnectionBadge } from "./live-connection-status.js";
import { tauriAudioState } from "./live-tauri-audio-state.js";

/**
 * Tauri 로컬 오디오 스트림 시작과 프리웜(미리 준비) 처리.
 */

export async function connectTauriLiveAudio(source) {
    const bridgeReady = await setupTauriLiveAudioBridge();
    if (!bridgeReady) {
        throw new Error("Tauri live audio bridge 초기화에 실패했습니다.");
    }
    const captureProfile = resolveLocalCaptureProfile(source);

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
        preprocess: captureProfile.preprocess,
    });

    tauriAudioState.streamActive = true;
    tauriAudioState.prewarmedSource = null;
    updateConnectionBadge("오디오 스트림 활성", "live");
}

export function resolveTauriPrewarmSource(source) {
    const connectionMode = resolveLiveConnectionMode(source, isTauriRuntime());
    if (
        connectionMode === LIVE_CONNECTION_MODE.SYSTEM_AUDIO_TAURI
        || connectionMode === LIVE_CONNECTION_MODE.MIXED_LOCAL_TAURI
    ) {
        return AUDIO_SOURCE.SYSTEM_AUDIO;
    }
    return null;
}

export async function ensureTauriLiveAudioPrewarmed(source) {
    const prewarmSource = resolveTauriPrewarmSource(source);
    if (!prewarmSource) {
        return false;
    }

    if (tauriAudioState.streamActive) {
        return true;
    }
    if (tauriAudioState.prewarmedSource === prewarmSource) {
        return true;
    }
    if (tauriAudioState.prewarmPromise) {
        return tauriAudioState.prewarmPromise;
    }

    tauriAudioState.prewarmPromise = (async () => {
        const bridgeReady = await setupTauriLiveAudioBridge();
        if (!bridgeReady) {
            return false;
        }

        const captureProfile = resolveLocalCaptureProfile(prewarmSource);
        await prewarmTauriLiveAudioStream({
            pythonExe: DEFAULT_BACKEND_PYTHON,
            scriptPath: DEFAULT_LIVE_AUDIO_SCRIPT_PATH,
            source: prewarmSource,
            sampleRate: DEFAULT_LIVE_AUDIO_SAMPLE_RATE,
            channels: DEFAULT_LIVE_AUDIO_CHANNELS,
            chunkMs: DEFAULT_LIVE_AUDIO_CHUNK_MS,
            preprocess: captureProfile.preprocess,
        });
        tauriAudioState.prewarmedSource = prewarmSource;
        return true;
    })();

    try {
        return await tauriAudioState.prewarmPromise;
    } catch (error) {
        tauriAudioState.prewarmedSource = null;
        console.warn("[CAPS] live audio prewarm 실패:", error);
        return false;
    } finally {
        tauriAudioState.prewarmPromise = null;
    }
}
