/** 오버레이에서 공통 흐름의 events board controller 제어를 담당한다. */
import { elements } from "../dom/elements.js";
import {
    renderEventColumn,
    renderManagedEventColumn,
} from "../renderers/cards.js";
import { fetchEventList } from "../services/api/events-api.js";
import { normalizeEventListPayload } from "../services/payload-normalizers.js";
import { appState } from "../state/app-state.js";
import { applyEventList } from "../state/events-store.js";
import { mergeOverviewBuckets } from "../state/session/overview-state.js";

const HIDDEN_EVENT_STATES = new Set(["answered", "resolved", "closed"]);

function filterVisibleEvents(grouped) {
    return {
        questions: grouped.questions.filter((item) => !HIDDEN_EVENT_STATES.has(item.state)),
        decisions: grouped.decisions.filter((item) => !HIDDEN_EVENT_STATES.has(item.state)),
        actionItems: grouped.actionItems.filter((item) => !HIDDEN_EVENT_STATES.has(item.state)),
        risks: grouped.risks.filter((item) => !HIDDEN_EVENT_STATES.has(item.state)),
    };
}

export function renderEventBoard() {
    const grouped = appState.events.items.length
        ? appState.events.grouped
        : mergeOverviewBuckets(appState.session.overview, appState.session.liveOverview);
    const visibleGrouped = filterVisibleEvents(grouped);
    const renderer = appState.events.items.length
        ? renderManagedEventColumn
        : renderEventColumn;

    renderColumn(renderer, elements.questionsList, elements.questionCount, visibleGrouped.questions);
    renderColumn(renderer, elements.decisionsList, elements.decisionCount, visibleGrouped.decisions);
    renderColumn(renderer, elements.actionsList, elements.actionCount, visibleGrouped.actionItems);
    renderColumn(renderer, elements.risksList, elements.riskCount, visibleGrouped.risks);
}

export async function refreshEventBoard() {
    if (!appState.session.id) {
        return;
    }

    try {
        const items = normalizeEventListPayload(await fetchEventList(appState.session.id));
        applyEventList(appState, items);
        renderEventBoard();
    } catch (error) {
        console.error(error);
    }
}

function renderColumn(renderer, container, countElement, items) {
    if (!container || !countElement || !elements.eventCardTemplate) {
        return;
    }

    renderer(
        {
            container,
            countElement,
            template: elements.eventCardTemplate,
        },
        items,
    );
}
