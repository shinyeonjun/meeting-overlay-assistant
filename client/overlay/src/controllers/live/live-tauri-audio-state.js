/**
 * Tauri 라이브 오디오 스트림의 공유 상태.
 * 여러 모듈(연결/프리웜/정지)이 같은 객체를 통해 읽고 갱신한다.
 */
export const tauriAudioState = {
    streamActive: false,
    prewarmedSource: null,
    prewarmPromise: null,
};
