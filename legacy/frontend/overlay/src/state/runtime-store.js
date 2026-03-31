import { isWebSpeechSupported } from "../services/web-speech-recognizer.js";

function isSourceReady(source, preloadedSources, bridgeReady) {
    const micReady = Boolean(preloadedSources.mic?.ready) || isWebSpeechSupported();
    const systemAudioReady = Boolean(preloadedSources.system_audio?.ready) && bridgeReady;

    if (source === "system_audio") {
        return systemAudioReady;
    }
    if (source === "mic_and_audio") {
        return micReady && systemAudioReady;
    }
    if (source === "mic") {
        return micReady;
    }
    if (source === "file") {
        return true;
    }
    return false;
}

export function applyRuntimeReadiness(state, payload, selectedSource) {
    state.runtime.backendReady = payload.backend_ready === true;
    state.runtime.sttReady = payload.stt_ready === true;
    state.runtime.warming = payload.warming !== false;
    state.runtime.preloadedSources = payload.preloaded_sources ?? {};
    state.runtime.selectedSource = selectedSource;
    state.runtime.selectedSourceReady = isSourceReady(
        selectedSource,
        state.runtime.preloadedSources,
        state.runtime.bridgeReady,
    );
    state.runtime.startReady = (
        state.runtime.backendReady
        && state.runtime.sttReady
        && state.runtime.selectedSourceReady
    );
    state.runtime.lastCheckedAt = Date.now();
}

export function setBridgeReady(state, bridgeReady, selectedSource) {
    state.runtime.bridgeReady = bridgeReady === true;
    state.runtime.selectedSource = selectedSource;
    state.runtime.selectedSourceReady = isSourceReady(
        selectedSource,
        state.runtime.preloadedSources,
        state.runtime.bridgeReady,
    );
    state.runtime.startReady = (
        state.runtime.backendReady
        && state.runtime.sttReady
        && state.runtime.selectedSourceReady
    );
}
