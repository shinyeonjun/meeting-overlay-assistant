/**
 * 회의 시작 버튼이 막힌 이유를 한국어 한 줄로 만든다. 막히지 않았으면 null.
 * 버튼 title과 시작 실패 안내가 같은 문장을 쓰도록 한 곳에 둔다.
 */

const SOURCE_LABELS = Object.freeze({
    mic: "마이크",
    system_audio: "시스템 오디오",
    mic_and_audio: "마이크 + 시스템 오디오",
    file: "오디오 파일",
});

export function resolveStartBlockReason({
    sessionId,
    sessionStatus,
    serverReady,
    clientReady,
    warming,
    source,
}) {
    if (!sessionId) {
        return "먼저 회의 세션을 만들어 주세요.";
    }
    if (sessionStatus !== "draft") {
        return "이미 시작되었거나 종료된 세션입니다.";
    }
    if (!serverReady) {
        return warming
            ? "서버와 STT 모델을 준비하는 중입니다. 잠시 기다려 주세요."
            : "서버에 연결할 수 없습니다. 서버가 실행 중인지 확인해 주세요.";
    }
    if (!clientReady) {
        const label = SOURCE_LABELS[source] ?? "선택한 입력";
        return `${label} 입력을 쓸 수 없습니다. 입력 장치와 설정을 확인해 주세요.`;
    }
    return null;
}
