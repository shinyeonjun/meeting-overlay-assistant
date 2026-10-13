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

function findCaptionLineBySegment(segmentId) {
    for (const line of elements.captionFeed.children) {
        if (line.dataset.feedKind === "caption" && line.dataset.segmentId === segmentId) {
            return line;
        }
    }
    return null;
}

/**
 * 끝난 자막 줄을 목록에 넣는다. 같은 구간(segmentId)의 줄이 이미 있으면 새로 추가하지 않고 글자만 고친다.
 * entry는 { text, segmentId } 또는 문자열이다.
 */
export function pushCaptionFeedLine(entry) {
    const text = typeof entry === "string" ? entry : entry?.text;
    const segmentId = typeof entry === "string" ? null : (entry?.segmentId ?? null);
    if (!text) {
        return;
    }

    if (segmentId) {
        const existing = findCaptionLineBySegment(segmentId);
        if (existing) {
            existing.textContent = text;
            existing.dataset.feedValue = text;
            return;
        }
    }

    const latestLine = elements.captionFeed.firstElementChild;
    if (latestLine?.dataset.feedKind === "caption" && latestLine.dataset.feedValue === text) {
        return;
    }

    const line = document.createElement("div");
    line.className = "feed-line";
    line.textContent = text;
    line.dataset.feedKind = "caption";
    line.dataset.feedValue = text;
    if (segmentId) {
        line.dataset.segmentId = segmentId;
    }
    elements.captionFeed.prepend(line);
    trimFeed();
}
