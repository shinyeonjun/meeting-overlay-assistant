/**
 * 라이브 컨트롤러 파사드
 *
 * - 연결/브리지: live/live-connection.js
 * - payload 처리: live/live-payload-handler.js
 * - 캡션 렌더링: live/live-caption-renderer.js
 */

export {
    connectLiveSource,
    sendDevText,
    setupTauriLiveAudioBridge,
    stopActiveLiveConnection,
} from "./live/live-connection.js";

