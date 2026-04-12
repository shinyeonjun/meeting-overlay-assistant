/** 오버레이에서 공통 흐름의 ui controller 제어를 담당한다. */
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
