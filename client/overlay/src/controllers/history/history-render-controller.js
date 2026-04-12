import { renderHistoryFocus } from "./detail-share-controller.js";
import { renderHistoryLists, renderHistoryScopeControls } from "./list-renderer.js";
import { renderWorkflowSummary } from "../ui/workflow-summary-controller.js";

export function renderHistoryBoard() {
    renderHistoryScopeControls();
    renderHistoryLists();
    renderHistoryFocus();
    renderWorkflowSummary();
}
