/** 오버레이 런타임에서 쓰는 constants 설정을 정의한다. */
function getNumberEnv(key, fallbackValue) {
    const rawValue = import.meta.env[key];
    const parsedValue = Number(rawValue);
    return Number.isFinite(parsedValue) ? parsedValue : fallbackValue;
}

export const POLLING_INTERVAL_MS = getNumberEnv("VITE_OVERVIEW_POLLING_INTERVAL_MS", 2500);
export const RUNTIME_READINESS_POLLING_INTERVAL_MS = getNumberEnv("VITE_RUNTIME_READINESS_POLLING_INTERVAL_MS", 3000);
export const DEV_TEXT_SEND_DELAY_MS = getNumberEnv("VITE_DEV_TEXT_SEND_DELAY_MS", 180);
export const DEV_TEXT_RETRY_DELAY_MS = getNumberEnv("VITE_DEV_TEXT_RETRY_DELAY_MS", 250);
export const TRANSCRIPT_TYPING_INTERVAL_MS = getNumberEnv("VITE_TRANSCRIPT_TYPING_INTERVAL_MS", 22);
export const TRANSCRIPT_HISTORY_LIMIT = getNumberEnv("VITE_TRANSCRIPT_HISTORY_LIMIT", 8);
export const ACTIVE_LINE_FINALIZE_TIMEOUT_MS = getNumberEnv("VITE_ACTIVE_LINE_FINALIZE_TIMEOUT_MS", 900);
export const ACTIVE_LINE_SOFT_DELAY_MS = getNumberEnv("VITE_ACTIVE_LINE_SOFT_DELAY_MS", 250);
