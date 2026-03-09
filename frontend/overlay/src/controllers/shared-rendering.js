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

const HIDDEN_EVENT_STATES = new Set(["answered", "confirmed", "resolved", "closed"]);

function filterVisibleEvents(grouped) {
    return {
        questions: grouped.questions.filter((item) => !HIDDEN_EVENT_STATES.has(item.state)),
        decisions: grouped.decisions.filter((item) => !HIDDEN_EVENT_STATES.has(item.state)),
        actionItems: grouped.actionItems.filter((item) => !HIDDEN_EVENT_STATES.has(item.state)),
        risks: grouped.risks.filter((item) => !HIDDEN_EVENT_STATES.has(item.state)),
    };
}

export function renderOverviewColumns() {
    const grouped = appState.events.items.length
        ? appState.events.grouped
        : appState.session.overview;
    const visibleGrouped = filterVisibleEvents(grouped);
    const renderer = appState.events.items.length
        ? renderManagedEventColumn
        : renderEventColumn;

    renderer(
        {
            container: elements.questionsList,
            countElement: elements.questionCount,
            template: elements.eventCardTemplate,
        },
        visibleGrouped.questions,
    );
    renderer(
        {
            container: elements.decisionsList,
            countElement: elements.decisionCount,
            template: elements.eventCardTemplate,
        },
        visibleGrouped.decisions,
    );
    renderer(
        {
            container: elements.actionsList,
            countElement: elements.actionCount,
            template: elements.eventCardTemplate,
        },
        visibleGrouped.actionItems,
    );
    renderer(
        {
            container: elements.risksList,
            countElement: elements.riskCount,
            template: elements.eventCardTemplate,
        },
        visibleGrouped.risks,
    );
}

export function renderReportPanels() {
    if (
        elements.speakerTranscriptList
        && elements.speakerTranscriptCount
        && elements.speakerTranscriptTemplate
    ) {
        renderSpeakerTranscript(
            {
                container: elements.speakerTranscriptList,
                countElement: elements.speakerTranscriptCount,
                template: elements.speakerTranscriptTemplate,
            },
            appState.report.speakerTranscript,
        );
    }

    if (
        elements.speakerEventsList
        && elements.speakerEventCount
        && elements.eventCardTemplate
    ) {
        renderSpeakerEvents(
            {
                container: elements.speakerEventsList,
                countElement: elements.speakerEventCount,
                template: elements.eventCardTemplate,
            },
            appState.report.speakerEvents,
        );
    }

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
