/**
 * 히스토리 상세/공유 façade.
 * 상세 조회, 포커스 렌더, 공유 액션은 하위 모듈로 분리한다.
 */

export { refreshSelectedHistoryDetails } from "./history-detail-refresh-controller.js";
export { renderHistoryFocus } from "./history-focus-renderer.js";
export { handleCreateShare } from "./history-share-action-controller.js";
