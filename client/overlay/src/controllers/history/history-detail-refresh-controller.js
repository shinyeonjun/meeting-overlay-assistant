import {
    getReportById,
    getSharedReportById,
    listReportShares,
} from "../../services/api/report-api.js";
import {
    normalizeReportDetailPayload,
    normalizeReportShareListPayload,
} from "../../services/payload-normalizers.js";
import { appState } from "../../state/app-state.js";
import {
    applyReportShares,
    clearHistoryDetails,
    clearReportShares,
    setHistoryDetailLoading,
    setHistoryReportContent,
    setHistoryShareLoading,
    setHistoryShareStatus,
} from "../../state/history-store.js";
import {
    canUseShareFeatures,
    resolveSelectedHistoryItem,
} from "./helpers.js";
import { renderHistoryFocus } from "./history-focus-renderer.js";

let detailRefreshPromise = null;

export async function refreshSelectedHistoryDetails({ preserveShareStatus = null } = {}) {
    if (detailRefreshPromise) {
        return detailRefreshPromise;
    }

    detailRefreshPromise = refreshSelectedHistoryDetailsInternal({
        preserveShareStatus,
    });

    try {
        await detailRefreshPromise;
    } finally {
        detailRefreshPromise = null;
    }
}

async function refreshSelectedHistoryDetailsInternal({ preserveShareStatus }) {
    const selectedItem = resolveSelectedHistoryItem();
    if (!selectedItem || appState.history.selectedKind === "session") {
        clearHistoryDetails(appState);
        renderHistoryFocus();
        return;
    }

    setHistoryDetailLoading(appState, true);
    if (appState.history.selectedKind === "report") {
        setHistoryShareLoading(appState, true);
    }
    renderHistoryFocus();

    try {
        if (appState.history.selectedKind === "report") {
            const [detailPayload, sharesPayload] = await Promise.all([
                getReportById(selectedItem.sessionId, selectedItem.id),
                canUseShareFeatures()
                    ? listReportShares(selectedItem.sessionId, selectedItem.id)
                    : Promise.resolve({ items: [] }),
            ]);

            const detail = normalizeReportDetailPayload(detailPayload);
            setHistoryReportContent(appState, detail.content ?? "");
            applyReportShares(appState, normalizeReportShareListPayload(sharesPayload));
            setHistoryShareStatus(
                appState,
                preserveShareStatus
                    ?? (appState.history.reportShares.length
                        ? "공유 목록을 불러왔습니다."
                        : "?꾩쭅 怨듭쑀 湲곕줉???놁뒿?덈떎."),
            );
        } else {
            const detailPayload = await getSharedReportById(selectedItem.reportId);
            const detail = normalizeReportDetailPayload(detailPayload);
            setHistoryReportContent(appState, detail.content ?? "");
            clearReportShares(appState);
            setHistoryShareStatus(appState, "");
        }
    } catch (error) {
        console.error("[CAPS] ?덉뒪?좊━ ?곸꽭 議고쉶 ?ㅽ뙣:", error);
        clearHistoryDetails(appState);
        setHistoryReportContent(
            appState,
            "?곸꽭 ?댁슜??遺덈윭?ㅼ? 紐삵뻽?듬땲?? ?쒕쾭 ?곹깭? 沅뚰븳???뺤씤??二쇱꽭??",
        );
        setHistoryShareStatus(appState, "?곸꽭 湲곕줉??遺덈윭?ㅼ? 紐삵뻽?듬땲??");
    }

    setHistoryDetailLoading(appState, false);
    setHistoryShareLoading(appState, false);
    renderHistoryFocus();
}

