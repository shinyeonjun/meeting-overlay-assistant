import { elements } from "../../dom/elements.js";
import { appState } from "../../state/app-state.js";
import {
    buildEmptyState,
    canUseShareFeatures,
    resolveEffectiveScope,
    resolveSelectedHistoryItem,
} from "./helpers.js";
import {
    extractFileLabel,
    formatDateTime,
    formatInsightSourceLabel,
    formatReportTypeLabel,
    formatSourceLabel,
    formatStatusLabel,
} from "./formatters.js";
import {
    renderCarryOverPanel,
    renderHistoryTimelinePanel,
    renderRetrievalBriefPanel,
} from "./timeline-renderer.js";

export function renderHistoryFocus() {
    if (!elements.historyFocusTitle || !elements.historyFocusMeta || !elements.historyFocusBody) {
        return;
    }

    renderHistoryTimelinePanel();
    renderCarryOverPanel();
    renderRetrievalBriefPanel();

    const selectedItem = resolveSelectedHistoryItem();

    if (appState.history.errorMessage) {
        elements.historyFocusTitle.textContent = "히스토리 로딩 실패";
        elements.historyFocusMeta.textContent = "오류";
        elements.historyFocusBody.textContent = appState.history.errorMessage;
        hidePreviewPanel();
        hideReceivedPanel();
        hideSharePanel();
        return;
    }

    if (!selectedItem) {
        elements.historyFocusTitle.textContent = "회의나 리포트를 선택해 주세요.";
        elements.historyFocusMeta.textContent =
            resolveEffectiveScope() === "all" ? "전체 범위" : "내 범위";
        elements.historyFocusBody.textContent =
            "왼쪽 목록이나 최근 기록 타임라인에서 항목을 고르면 요약, 본문 미리보기, 공유 정보를 이어서 확인할 수 있습니다.";
        hidePreviewPanel();
        hideReceivedPanel();
        hideSharePanel();
        return;
    }

    if (appState.history.selectedKind === "session") {
        elements.historyFocusTitle.textContent = selectedItem.title || "제목 없는 회의";
        elements.historyFocusMeta.textContent =
            `${formatStatusLabel(selectedItem.status)} / ${formatDateTime(selectedItem.startedAt)}`;
        elements.historyFocusBody.textContent = [
            `시작 시각: ${formatDateTime(selectedItem.startedAt)}`,
            `진행 상태: ${formatStatusLabel(selectedItem.status)}`,
            `입력 방식: ${formatSourceLabel(selectedItem.primaryInputSource)}`,
            `실제 입력: ${selectedItem.actualActiveSources?.map(formatSourceLabel).join(", ") || "자동 감지 대기"}`,
        ].join("\n");
        hidePreviewPanel();
        hideReceivedPanel();
        hideSharePanel();
        return;
    }

    if (appState.history.selectedKind === "report") {
        elements.historyFocusTitle.textContent =
            `${formatReportTypeLabel(selectedItem.reportType)} / v${selectedItem.version}`;
        elements.historyFocusMeta.textContent =
            `내 리포트 / ${formatDateTime(selectedItem.generatedAt)}`;
        elements.historyFocusBody.textContent = [
            `리포트 형식: ${formatReportTypeLabel(selectedItem.reportType)}`,
            `생성 시각: ${formatDateTime(selectedItem.generatedAt)}`,
            `파일 이름: ${extractFileLabel(selectedItem.filePath)}`,
            `정리 방식: ${formatInsightSourceLabel(selectedItem.insightSource)}`,
        ].join("\n");
        renderPreviewPanel({
            title: "리포트 본문",
            content: appState.history.selectedReportContent,
        });
        hideReceivedPanel();
        renderSharePanel(selectedItem);
        return;
    }

    elements.historyFocusTitle.textContent =
        `${formatReportTypeLabel(selectedItem.reportType)} / v${selectedItem.version}`;
    elements.historyFocusMeta.textContent =
        `${selectedItem.sharedByDisplayName} 공유 / ${formatDateTime(selectedItem.sharedAt)}`;
    elements.historyFocusBody.textContent = [
        `보낸 사람: ${selectedItem.sharedByDisplayName} (${selectedItem.sharedByLoginId})`,
        `공유 시각: ${formatDateTime(selectedItem.sharedAt)}`,
        `파일 이름: ${selectedItem.fileName || extractFileLabel(selectedItem.filePath)}`,
        `정리 방식: ${formatInsightSourceLabel(selectedItem.insightSource)}`,
    ].join("\n");
    renderPreviewPanel({
        title: "공유받은 리포트 본문",
        content: appState.history.selectedReportContent,
    });
    renderReceivedPanel(selectedItem);
    hideSharePanel();
}

function renderPreviewPanel({ title, content }) {
    if (!elements.historyPreviewPanel || !elements.historyPreviewTitle || !elements.historyPreviewBody) {
        return;
    }

    elements.historyPreviewPanel.classList.remove("hidden");
    elements.historyPreviewTitle.textContent = title;

    if (appState.history.detailLoading) {
        elements.historyPreviewBody.textContent = "리포트 본문을 불러오는 중입니다.";
        return;
    }

    elements.historyPreviewBody.textContent = content?.trim() || "표시할 본문이 없습니다.";
}

function hidePreviewPanel() {
    elements.historyPreviewPanel?.classList.add("hidden");
}

function renderReceivedPanel(sharedReport) {
    if (!elements.historyReceivedPanel || !elements.historyReceivedFrom || !elements.historyReceivedMeta) {
        return;
    }

    elements.historyReceivedPanel.classList.remove("hidden");
    elements.historyReceivedFrom.textContent = `${sharedReport.sharedByDisplayName}님의 전달 자료`;
    elements.historyReceivedMeta.textContent = [
        `권한 ${sharedReport.permission}`,
        sharedReport.note ? `메모 ${sharedReport.note}` : null,
    ].filter(Boolean).join(" / ");
}

function hideReceivedPanel() {
    elements.historyReceivedPanel?.classList.add("hidden");
}

function renderSharePanel(selectedReport) {
    if (
        !elements.historySharePanel
        || !elements.historyShareStatus
        || !elements.historyShareList
        || !canUseShareFeatures()
    ) {
        hideSharePanel();
        return;
    }

    elements.historySharePanel.classList.remove("hidden");

    if (elements.historyShareButton) {
        elements.historyShareButton.disabled = appState.history.shareLoading;
    }
    if (elements.historyShareLoginId) {
        elements.historyShareLoginId.disabled = appState.history.shareLoading;
    }
    if (elements.historyShareNote) {
        elements.historyShareNote.disabled = appState.history.shareLoading;
    }

    elements.historyShareStatus.textContent =
        appState.history.shareStatusText
        || `${formatReportTypeLabel(selectedReport.reportType)} v${selectedReport.version}를 바로 전달할 수 있습니다.`;

    elements.historyShareList.replaceChildren();

    if (appState.history.shareLoading) {
        elements.historyShareList.append(buildEmptyState("공유 목록을 불러오는 중입니다."));
        return;
    }

    if (!appState.history.reportShares.length) {
        elements.historyShareList.append(buildEmptyState("아직 공유 기록이 없습니다."));
        return;
    }

    for (const item of appState.history.reportShares) {
        const card = document.createElement("div");
        card.className = "history-share-item";

        const title = document.createElement("span");
        title.className = "history-share-item-title";
        title.textContent = item.sharedWithDisplayName;

        const meta = document.createElement("span");
        meta.className = "history-share-item-meta";
        meta.textContent = [
            item.sharedWithLoginId,
            `보낸 사람 ${item.sharedByDisplayName}`,
            `공유 ${formatDateTime(item.createdAt)}`,
            item.note ? `메모 ${item.note}` : null,
        ].filter(Boolean).join(" / ");

        card.append(title, meta);
        elements.historyShareList.append(card);
    }
}

function hideSharePanel() {
    elements.historySharePanel?.classList.add("hidden");
}
