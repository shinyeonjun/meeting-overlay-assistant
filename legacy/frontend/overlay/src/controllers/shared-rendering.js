import { elements } from "../dom/elements.js";
import {
    renderEventColumn,
    renderManagedEventColumn,
} from "../renderers/cards.js";
import { fetchEventList, fetchOverview } from "../services/api-client.js";
import {
    normalizeEventListPayload,
    normalizeOverviewPayload,
} from "../services/payload-normalizers.js";
import { appState } from "../state/app-state.js";
import { applyEventList } from "../state/events-store.js";
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
