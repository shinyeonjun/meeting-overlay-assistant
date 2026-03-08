/**
 * 공유 렌더링 유틸리티
 *
 * session-controller와 live-controller에서 공통으로 사용한다.
 */

import { elements } from "../dom/elements.js";
import {
    renderEventColumn,
    renderManagedEventColumn,
    renderSpeakerEvents,
    renderSpeakerTranscript,
} from "../renderers/cards.js";
import { fetchEventList, fetchOverview, fetchReportList } from "../services/api-client.js";
import {
    normalizeEventListPayload,
    normalizeOverviewPayload,
    normalizeReportListPayload,
} from "../services/payload-normalizers.js";
import { appState } from "../state/app-state.js";
import { applyEventList } from "../state/events-store.js";
import { applyReportHistory } from "../state/report-store.js";
import { applyOverview } from "../state/session-store.js";
import { pushEventFeed } from "./live/live-feed.js";

/** 4개 이벤트 컬럼을 렌더링한다. */
export function renderOverviewColumns() {
    const grouped = appState.events.items.length
        ? appState.events.grouped
        : appState.session.overview;
    const renderer = appState.events.items.length
        ? renderManagedEventColumn
        : renderEventColumn;

    renderer(
        {
            container: elements.questionsList,
            countElement: elements.questionCount,
            template: elements.eventCardTemplate,
            selectedIds: appState.events.selectedIds,
        },
        grouped.questions,
    );
    renderer(
        {
            container: elements.decisionsList,
            countElement: elements.decisionCount,
            template: elements.eventCardTemplate,
            selectedIds: appState.events.selectedIds,
        },
        grouped.decisions,
    );
    renderer(
        {
            container: elements.actionsList,
            countElement: elements.actionCount,
            template: elements.eventCardTemplate,
            selectedIds: appState.events.selectedIds,
        },
        grouped.actionItems,
    );
    renderer(
        {
            container: elements.risksList,
            countElement: elements.riskCount,
            template: elements.eventCardTemplate,
            selectedIds: appState.events.selectedIds,
        },
        grouped.risks,
    );

    renderEventToolbar();
}

export function renderEventToolbar() {
    if (!elements.selectedEventCount) {
        return;
    }

    const selectedCount = appState.events.selectedIds.size;
    elements.selectedEventCount.textContent = `${selectedCount} selected`;

    if (elements.bulkConfirmEventsButton) {
        elements.bulkConfirmEventsButton.disabled = selectedCount === 0;
    }
    if (elements.bulkCloseEventsButton) {
        elements.bulkCloseEventsButton.disabled = selectedCount === 0;
    }
    if (elements.clearSelectedEventsButton) {
        elements.clearSelectedEventsButton.disabled = selectedCount === 0;
    }
}

/** 리포트 패널(화자별 전사, 이벤트)을 렌더링한다. */
export function renderReportPanels() {
    renderSpeakerTranscript(
        {
            container: elements.speakerTranscriptList,
            countElement: elements.speakerTranscriptCount,
            template: elements.speakerTranscriptTemplate,
        },
        appState.report.speakerTranscript,
    );
    renderSpeakerEvents(
        {
            container: elements.speakerEventsList,
            countElement: elements.speakerEventCount,
            template: elements.eventCardTemplate,
        },
        appState.report.speakerEvents,
    );

    renderReportHistory();
}

export function renderReportHistory() {
    if (!elements.reportHistoryList || !elements.reportHistoryCount) {
        return;
    }

    elements.reportHistoryCount.textContent = String(appState.report.history.length);
    elements.reportHistoryList.replaceChildren();

    if (!appState.report.history.length) {
        const empty = document.createElement("div");
        empty.className = "event-empty";
        empty.textContent = "아직 생성된 리포트가 없습니다.";
        elements.reportHistoryList.append(empty);
        return;
    }

    for (const item of [...appState.report.history].reverse()) {
        const row = document.createElement("button");
        row.type = "button";
        row.className = "report-history-item";
        row.dataset.reportId = item.id;
        row.textContent = `${item.reportType.toUpperCase()} v${item.version ?? "?"}`;
        if (appState.report.latestReportId === item.id) {
            row.classList.add("active");
        }
        elements.reportHistoryList.append(row);
    }
}

/** 서버에서 최신 overview를 받아와 상태/화면에 반영한다. */
export async function refreshOverview() {
    if (!appState.session.id) {
        return;
    }

    try {
        const overviewPayload = normalizeOverviewPayload(await fetchOverview(appState.session.id));
        applyOverview(appState, overviewPayload);

        elements.currentTopic.textContent = overviewPayload.currentTopic ?? "아직 감지된 주제가 없습니다.";

        renderOverviewColumns();
        pushEventFeed("question", appState.session.overview.questions);
        pushEventFeed("decision", appState.session.overview.decisions);
        pushEventFeed("action_item", appState.session.overview.actionItems);
        pushEventFeed("risk", appState.session.overview.risks);
    } catch (error) {
        console.error(error);
    }
}

export async function refreshEventBoard() {
    if (!appState.session.id) {
        return;
    }

    try {
        const items = normalizeEventListPayload(await fetchEventList(appState.session.id));
        applyEventList(appState, items);
        renderOverviewColumns();
    } catch (error) {
        console.error(error);
    }
}

export async function refreshReportHistory() {
    if (!appState.session.id) {
        return;
    }

    try {
        const items = normalizeReportListPayload(await fetchReportList(appState.session.id));
        applyReportHistory(appState, items);
        renderReportHistory();
    } catch (error) {
        console.error(error);
    }
}
