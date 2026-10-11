/**
 * 마이크 입력 엔진 선택.
 *
 * - local: 로컬 STT (Tauri 앱의 백엔드 STT). 음성이 PC 밖으로 나가지 않는다. 기본값.
 * - web_speech: 브라우저 Web Speech API. 음성이 외부 서비스로 전송된다. 사용자가 직접 켠다.
 */

export const MIC_ENGINE = Object.freeze({
    LOCAL: "local",
    WEB_SPEECH: "web_speech",
});

export const DEFAULT_MIC_ENGINE = MIC_ENGINE.LOCAL;

const STORAGE_KEY = "caps.micEngine";

export function normalizeMicEngine(value) {
    return value === MIC_ENGINE.WEB_SPEECH ? MIC_ENGINE.WEB_SPEECH : DEFAULT_MIC_ENGINE;
}

export function readMicEngine() {
    try {
        return normalizeMicEngine(localStorage.getItem(STORAGE_KEY));
    } catch {
        // localStorage를 쓸 수 없으면 기본값을 쓴다.
        return DEFAULT_MIC_ENGINE;
    }
}

export function writeMicEngine(value) {
    const engine = normalizeMicEngine(value);
    try {
        localStorage.setItem(STORAGE_KEY, engine);
    } catch {
        // 저장하지 못해도 이번 세션에서는 선택이 적용된다.
    }
    return engine;
}
