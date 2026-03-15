/**
 * 히스토리 컨트롤러 façade.
 * 목록 이벤트, 데이터 갱신, 렌더링 책임은 history 하위 모듈로 분리한다.
 */

export { setupHistoryControls } from "./history/history-events-controller.js";
export {
    refreshHistoryBoard,
    refreshHistorySnapshot,
    resetHistoryBoard,
} from "./history/history-refresh-controller.js";
export { renderHistoryBoard } from "./history/history-render-controller.js";
