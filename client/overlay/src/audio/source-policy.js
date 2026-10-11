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
    MIXED_LOCAL_TAURI: "mixed_local_tauri",
    MIXED_LOCAL_UNSUPPORTED: "mixed_local_unsupported",
    TEXT_SOCKET: "text_socket",
});

export function isClientSourceReady(source, preloadedSources, bridgeReady) {
    const micReady = Boolean(preloadedSources.mic?.ready);
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
        return tauriRuntime
            ? LIVE_CONNECTION_MODE.MIC_LOCAL_TAURI
            : LIVE_CONNECTION_MODE.MIC_LOCAL_UNSUPPORTED;
    }
    if (source === AUDIO_SOURCE.MIXED) {
        return tauriRuntime
            ? LIVE_CONNECTION_MODE.MIXED_LOCAL_TAURI
            : LIVE_CONNECTION_MODE.MIXED_LOCAL_UNSUPPORTED;
    }
    return LIVE_CONNECTION_MODE.TEXT_SOCKET;
}
