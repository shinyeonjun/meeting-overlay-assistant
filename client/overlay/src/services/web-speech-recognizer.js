/** 오버레이에서 공통 관련 web speech recognizer 서비스를 제공한다. */
const RESTART_DELAY_MS = 150;

function resolveRecognitionClass() {
    if (typeof window === "undefined") {
        return null;
    }
    return window.SpeechRecognition ?? window.webkitSpeechRecognition ?? null;
}

export function isWebSpeechSupported() {
    return Boolean(resolveRecognitionClass());
}

export function createWebSpeechRecognizer({
    lang = "ko-KR",
    interimResults = true,
    continuous = true,
    onInterim,
    onFinal,
    onStart,
    onEnd,
    onError,
} = {}) {
    const RecognitionClass = resolveRecognitionClass();
    if (!RecognitionClass) {
        throw new Error("Web Speech API를 지원하지 않는 환경입니다.");
    }

    const recognition = new RecognitionClass();
    recognition.lang = lang;
    recognition.interimResults = interimResults;
    recognition.continuous = continuous;
    recognition.maxAlternatives = 1;

    let shouldRun = false;
    let isStarting = false;

    recognition.onstart = () => {
        isStarting = false;
        onStart?.();
    };

    recognition.onend = () => {
        onEnd?.();
        if (!shouldRun) {
            return;
        }
        window.setTimeout(() => {
            if (!shouldRun) {
                return;
            }
            try {
                isStarting = true;
                recognition.start();
            } catch (error) {
                isStarting = false;
                onError?.(error, { fatal: false, code: "restart_failed" });
            }
        }, RESTART_DELAY_MS);
    };

    recognition.onerror = (event) => {
        const code = event?.error ?? "unknown";
        const fatal = code === "not-allowed" || code === "service-not-allowed" || code === "audio-capture";
        if (fatal) {
            shouldRun = false;
        }
        onError?.(new Error(`Web Speech 오류: ${code}`), { fatal, code });
    };

    recognition.onresult = (event) => {
        for (let i = event.resultIndex; i < event.results.length; i += 1) {
            const result = event.results[i];
            const transcript = result?.[0]?.transcript?.trim() ?? "";
            if (!transcript) {
                continue;
            }

            if (result.isFinal) {
                onFinal?.(transcript);
            } else {
                onInterim?.(transcript);
            }
        }
    };

    return {
        start() {
            if (shouldRun || isStarting) {
                return;
            }
            shouldRun = true;
            try {
                isStarting = true;
                recognition.start();
            } catch (error) {
                isStarting = false;
                shouldRun = false;
                throw error;
            }
        },
        stop() {
            shouldRun = false;
            isStarting = false;
            try {
                recognition.stop();
            } catch {
                // 이미 중지된 상태면 무시한다.
            }
        },
        isRunning() {
            return shouldRun;
        },
    };
}

