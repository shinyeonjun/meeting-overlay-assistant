/** 오버레이에서 실시간 흐름의 live feed 제어를 담당한다. */
import { elements } from "../../dom/elements.js";
import { appState } from "../../state/app-state.js";
import { hasSeenFeedEvent, markFeedEventSeen } from "../../state/live-store.js";

const FEED_MAX = 8;

function trimFeed() {
    while (elements.captionFeed.children.length > FEED_MAX) {
        elements.captionFeed.removeChild(elements.captionFeed.lastElementChild);
    }
}

function getEventLabel(eventType) {
    if (eventType === "question") return "질문";
    if (eventType === "decision") return "결정";
    if (eventType === "action_item") return "액션";
    if (eventType === "risk") return "리스크";
    return eventType;
}

export function pushEventFeed(eventType, items) {
    for (const item of items) {
        const eventKey = item.id ?? `${eventType}:${item.title}`;
        if (hasSeenFeedEvent(appState, eventKey)) {
            continue;
        }

        markFeedEventSeen(appState, eventKey);

        const line = document.createElement("div");
        line.className = "feed-event";
        line.dataset.type = eventType;
        line.textContent = `${getEventLabel(eventType)} ${item.speaker_label ? `${item.speaker_label}: ` : ""}${item.title}`;
        elements.captionFeed.prepend(line);
        trimFeed();
    }
}

export function pushOverviewEventFeed(overview) {
    pushEventFeed("question", overview.questions);
    pushEventFeed("decision", overview.decisions);
    pushEventFeed("action_item", overview.actionItems);
    pushEventFeed("risk", overview.risks);
}

export function pushCaptionFeedLine(text) {
    const latestLine = elements.captionFeed.firstElementChild;
    if (latestLine?.dataset.feedKind === "caption" && latestLine.dataset.feedValue === text) {
        return;
    }

    const line = document.createElement("div");
    line.className = "feed-line";
    line.textContent = text;
    line.dataset.feedKind = "caption";
    line.dataset.feedValue = text;
    elements.captionFeed.prepend(line);
    trimFeed();
}
