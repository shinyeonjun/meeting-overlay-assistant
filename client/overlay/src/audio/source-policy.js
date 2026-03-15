import { isWebSpeechSupported } from "../services/web-speech-recognizer.js";

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
    MIC_WEB_SPEECH: "mic_web_speech",
    MIXED_BROWSER: "mixed_browser",
    MIXED_TAURI: "mixed_tauri",
    TEXT_SOCKET: "text_socket",
});

export function isClientSourceReady(source, preloadedSources, bridgeReady) {
    const micReady = Boolean(preloadedSources.mic?.ready) || isWebSpeechSupported();
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

export function resolveLiveConnectionMode(source, tauriRuntime) {
    if (source === AUDIO_SOURCE.FILE) {
        return LIVE_CONNECTION_MODE.FILE_IDLE;
    }
    if (source === AUDIO_SOURCE.SYSTEM_AUDIO) {
        return tauriRuntime
            ? LIVE_CONNECTION_MODE.SYSTEM_AUDIO_TAURI
            : LIVE_CONNECTION_MODE.SYSTEM_AUDIO_UNSUPPORTED;
    }
    if (source === AUDIO_SOURCE.MIC) {
        return LIVE_CONNECTION_MODE.MIC_WEB_SPEECH;
    }
    if (source === AUDIO_SOURCE.MIXED) {
        return tauriRuntime
            ? LIVE_CONNECTION_MODE.MIXED_TAURI
            : LIVE_CONNECTION_MODE.MIXED_BROWSER;
    }
    return LIVE_CONNECTION_MODE.TEXT_SOCKET;
}
