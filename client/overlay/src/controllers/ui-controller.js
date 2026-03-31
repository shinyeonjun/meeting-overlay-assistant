/**
 * UI 컨트롤러 façade.
 * Tauri 브리지, 드래그 레이아웃, 워크스페이스 전환, 상태 배지는 하위 모듈로 분리한다.
 */

export {
    sendUIRects,
    setupTauriUiBridge,
} from "./ui/ui-bridge-controller.js";
export { setupDraggableLayout } from "./ui/ui-layout-controller.js";
export {
    activateTab,
    closeWorkspace,
    openWorkspace,
    toggleCaptionBody,
} from "./ui/ui-workspace-controller.js";
export { openWebWorkspace } from "./ui/ui-web-workspace-controller.js";
export {
    flashStatus,
    setStatus,
} from "./ui/ui-status-controller.js";
