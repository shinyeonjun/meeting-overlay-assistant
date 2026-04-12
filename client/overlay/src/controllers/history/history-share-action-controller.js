import { elements } from "../../dom/elements.js";
import { createReportShare } from "../../services/api/report-api.js";
import { normalizeReportSharePayload } from "../../services/payload-normalizers.js";
import { appState } from "../../state/app-state.js";
import {
    setHistoryShareLoading,
    setHistoryShareStatus,
} from "../../state/history-store.js";
import { getSelectedOwnReport } from "./helpers.js";
import { refreshSelectedHistoryDetails } from "./history-detail-refresh-controller.js";
import { renderHistoryFocus } from "./history-focus-renderer.js";

export async function handleCreateShare() {
    const selectedReport = getSelectedOwnReport();
    if (!selectedReport) {
        setHistoryShareStatus(appState, "공유할 리포트를 먼저 선택해 주세요.");
        renderHistoryFocus();
        return;
    }

    const sharedWithLoginId = elements.historyShareLoginId?.value.trim() ?? "";
    const note = elements.historyShareNote?.value.trim() ?? "";

    if (!sharedWithLoginId) {
        setHistoryShareStatus(appState, "받는 사람 로그인 아이디를 입력해 주세요.");
        renderHistoryFocus();
        return;
    }

    setHistoryShareLoading(appState, true);
    setHistoryShareStatus(appState, "리포트를 공유하는 중입니다.");
    renderHistoryFocus();

    try {
        const payload = await createReportShare(selectedReport.sessionId, selectedReport.id, {
            sharedWithLoginId,
            note,
        });
        const createdShare = normalizeReportSharePayload(payload);
        const successMessage = `${createdShare.sharedWithDisplayName}에게 공유했습니다.`;

        if (elements.historyShareLoginId) {
            elements.historyShareLoginId.value = "";
        }
        if (elements.historyShareNote) {
            elements.historyShareNote.value = "";
        }

        await refreshSelectedHistoryDetails({ preserveShareStatus: successMessage });
    } catch (error) {
        console.error("[CAPS] 리포트 공유 실패:", error);
        setHistoryShareLoading(appState, false);
        setHistoryShareStatus(appState, resolveShareErrorMessage(error));
        renderHistoryFocus();
    }
}

function resolveShareErrorMessage(error) {
    const rawMessage = String(error?.message ?? "");
    if (rawMessage.includes("409")) {
        return "이미 같은 사용자에게 공유한 리포트입니다.";
    }
    if (rawMessage.includes("404")) {
        return "공유 대상을 찾지 못했습니다.";
    }
    if (rawMessage.includes("400")) {
        return "공유 대상을 다시 확인해 주세요.";
    }
    return "리포트 공유에 실패했습니다. 서버 상태를 확인해 주세요.";
}
