import { isWebSpeechSupported } from "../services/web-speech-recognizer.js";
import { MIC_ENGINE, readMicEngine } from "./mic-engine.js";

export const AUDIO_SOURCE = Object.freeze({
    MIC: "mic",
    FILE: "file",
    MIXED: "mic_and_audio",
    SYSTEM_AUDIO: "system_audio",
});

export const LIVE_CONNECTION_MODE = Object.freeze({
    FILE_IDLE: "file_idle",
    SYSTEM_AUDIO_TAURI: "system_audio_tauri",
    SYSTEM_AUDIO_UNSUPPORTED: "system_audio_unsupported",
    MIC_LOCAL_TAURI: "mic_local_tauri",
    MIC_LOCAL_UNSUPPORTED: "mic_local_unsupported",
    MIC_WEB_SPEECH: "mic_web_speech",
    MIXED_LOCAL_TAURI: "mixed_local_tauri",
    MIXED_LOCAL_UNSUPPORTED: "mixed_local_unsupported",
    MIXED_BROWSER: "mixed_browser",
    MIXED_TAURI: "mixed_tauri",
    TEXT_SOCKET: "text_socket",
});

export function isClientSourceReady(
    source,
    preloadedSources,
    bridgeReady,
    micEngine = readMicEngine(),
) {
    // 로컬 STT 마이크는 백엔드 준비 상태로 판단한다. Web Speech는 사용자가 켠 경우에만 쓴다.
    const webSpeechReady = micEngine === MIC_ENGINE.WEB_SPEECH && isWebSpeechSupported();
    const micReady = Boolean(preloadedSources.mic?.ready) || webSpeechReady;
    const systemAudioReady = Boolean(preloadedSources.system_audio?.ready) && bridgeReady;

    if (source === AUDIO_SOURCE.SYSTEM_AUDIO) {
        return systemAudioReady;
    }
    if (source === AUDIO_SOURCE.MIXED) {
        return micReady && systemAudioReady;
    }
    if (source === AUDIO_SOURCE.MIC) {
        return micReady;
    }
    if (source === AUDIO_SOURCE.FILE) {
        return true;
    }
    return false;
}

export function resolveLiveConnectionMode(source, tauriRuntime, micEngine = readMicEngine()) {
    const useWebSpeech = micEngine === MIC_ENGINE.WEB_SPEECH;

    if (source === AUDIO_SOURCE.FILE) {
        return LIVE_CONNECTION_MODE.FILE_IDLE;
    }
    if (source === AUDIO_SOURCE.SYSTEM_AUDIO) {
        return tauriRuntime
            ? LIVE_CONNECTION_MODE.SYSTEM_AUDIO_TAURI
            : LIVE_CONNECTION_MODE.SYSTEM_AUDIO_UNSUPPORTED;
    }
    if (source === AUDIO_SOURCE.MIC) {
        if (useWebSpeech) {
            return LIVE_CONNECTION_MODE.MIC_WEB_SPEECH;
        }
        return tauriRuntime
            ? LIVE_CONNECTION_MODE.MIC_LOCAL_TAURI
            : LIVE_CONNECTION_MODE.MIC_LOCAL_UNSUPPORTED;
    }
    if (source === AUDIO_SOURCE.MIXED) {
        if (!useWebSpeech) {
            return tauriRuntime
                ? LIVE_CONNECTION_MODE.MIXED_LOCAL_TAURI
                : LIVE_CONNECTION_MODE.MIXED_LOCAL_UNSUPPORTED;
        }
        return tauriRuntime
            ? LIVE_CONNECTION_MODE.MIXED_TAURI
            : LIVE_CONNECTION_MODE.MIXED_BROWSER;
    }
    return LIVE_CONNECTION_MODE.TEXT_SOCKET;
}
