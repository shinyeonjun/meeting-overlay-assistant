import {
    DEFAULT_AUDIO_SILENCE_GATE_ENABLED,
    DEFAULT_AUDIO_SILENCE_GATE_HOLD_CHUNKS,
    DEFAULT_AUDIO_SILENCE_GATE_MIN_RMS,
} from "../config/defaults.js";
import { AUDIO_SOURCE } from "./source-policy.js";

function buildDefaultPreprocessProfile() {
    return {
        silenceGateEnabled: DEFAULT_AUDIO_SILENCE_GATE_ENABLED,
        silenceGateMinRms: DEFAULT_AUDIO_SILENCE_GATE_MIN_RMS,
        silenceGateHoldChunks: DEFAULT_AUDIO_SILENCE_GATE_HOLD_CHUNKS,
    };
}

export function resolveLocalCaptureProfile(source) {
    const preprocess = buildDefaultPreprocessProfile();

    if (source === AUDIO_SOURCE.FILE) {
        return {
            source,
            preprocess,
        };
    }

    if (source === AUDIO_SOURCE.MIC) {
        return {
            source,
            preprocess,
        };
    }

    if (source === AUDIO_SOURCE.SYSTEM_AUDIO) {
        return {
            source,
            preprocess,
        };
    }

    return {
        source,
        preprocess,
    };
}
