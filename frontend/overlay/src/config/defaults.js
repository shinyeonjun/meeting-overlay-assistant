function getStringEnv(key, fallbackValue = "") {
    const rawValue = import.meta.env[key];
    return typeof rawValue === "string" && rawValue.trim() ? rawValue.trim() : fallbackValue;
}

function getNumberEnv(key, fallbackValue) {
    const rawValue = Number(import.meta.env[key]);
    return Number.isFinite(rawValue) ? rawValue : fallbackValue;
}

export const DEFAULT_SESSION_TITLE = getStringEnv("VITE_DEFAULT_SESSION_TITLE", "오버레이 데모 세션");
export const DEFAULT_REPORT_AUDIO_PATH = getStringEnv("VITE_DEFAULT_REPORT_AUDIO_PATH", "");
export const DEFAULT_BACKEND_PYTHON = getStringEnv("VITE_BACKEND_PYTHON", "D:\\caps\\venv\\Scripts\\python.exe");
export const DEFAULT_LIVE_AUDIO_SCRIPT_PATH = getStringEnv(
    "VITE_LIVE_AUDIO_SCRIPT_PATH",
    "D:\\caps\\backend\\scripts\\stream_live_audio_ws.py",
);
export const DEFAULT_LIVE_AUDIO_SAMPLE_RATE = getNumberEnv("VITE_LIVE_AUDIO_SAMPLE_RATE", 16000);
export const DEFAULT_LIVE_AUDIO_CHANNELS = getNumberEnv("VITE_LIVE_AUDIO_CHANNELS", 1);
export const DEFAULT_LIVE_AUDIO_CHUNK_MS = getNumberEnv("VITE_LIVE_AUDIO_CHUNK_MS", 250);
export const DEFAULT_WEB_SPEECH_LANG = getStringEnv("VITE_WEB_SPEECH_LANG", "ko-KR");
