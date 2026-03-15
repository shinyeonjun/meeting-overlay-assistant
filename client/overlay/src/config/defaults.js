function getStringEnv(key, fallbackValue = "") {
    const rawValue = import.meta.env[key];
    return typeof rawValue === "string" && rawValue.trim() ? rawValue.trim() : fallbackValue;
}

function getNumberEnv(key, fallbackValue) {
    const rawValue = Number(import.meta.env[key]);
    return Number.isFinite(rawValue) ? rawValue : fallbackValue;
}

function getBooleanEnv(key, fallbackValue = false) {
    const rawValue = String(import.meta.env[key] ?? "").trim().toLowerCase();
    if (rawValue === "true" || rawValue === "1" || rawValue === "yes" || rawValue === "on") {
        return true;
    }
    if (rawValue === "false" || rawValue === "0" || rawValue === "no" || rawValue === "off") {
        return false;
    }
    return fallbackValue;
}

export const DEFAULT_SESSION_TITLE = getStringEnv("VITE_DEFAULT_SESSION_TITLE", "오버레이 데모 세션");
export const DEFAULT_BACKEND_PYTHON = getStringEnv("VITE_BACKEND_PYTHON", "D:\\caps\\venv\\Scripts\\python.exe");
export const DEFAULT_LIVE_AUDIO_SCRIPT_PATH = getStringEnv(
    "VITE_LIVE_AUDIO_SCRIPT_PATH",
    "D:\\caps\\server\\scripts\\audio\\stream_live_audio_ws.py",
);
export const DEFAULT_LIVE_AUDIO_SAMPLE_RATE = getNumberEnv("VITE_LIVE_AUDIO_SAMPLE_RATE", 16000);
export const DEFAULT_LIVE_AUDIO_CHANNELS = getNumberEnv("VITE_LIVE_AUDIO_CHANNELS", 1);
export const DEFAULT_LIVE_AUDIO_CHUNK_MS = getNumberEnv("VITE_LIVE_AUDIO_CHUNK_MS", 250);
export const DEFAULT_AUDIO_SILENCE_GATE_ENABLED = getBooleanEnv("VITE_AUDIO_SILENCE_GATE_ENABLED", false);
export const DEFAULT_AUDIO_SILENCE_GATE_MIN_RMS = getNumberEnv("VITE_AUDIO_SILENCE_GATE_MIN_RMS", 0.012);
export const DEFAULT_AUDIO_SILENCE_GATE_HOLD_CHUNKS = getNumberEnv("VITE_AUDIO_SILENCE_GATE_HOLD_CHUNKS", 2);
export const DEFAULT_WEB_SPEECH_LANG = getStringEnv("VITE_WEB_SPEECH_LANG", "ko-KR");

