import { elements } from "../../dom/elements.js";
import { appState } from "../../state/app-state.js";
import { hasSeenFeedEvent, markFeedEventSeen } from "../../state/live-store.js";
import {
    shouldKeepCaptionFeedOpen,
    shouldMergeCaptionFeedLine,
} from "./live-caption-policy.js";

const FEED_MAX = 8;

function trimFeed() {
    while (elements.captionFeed.children.length > FEED_MAX) {
        elements.captionFeed.removeChild(elements.captionFeed.lastElementChild);
    }
}

function getEventLabel(eventType) {
    if (eventType === "question") return "질문";
    return eventType;
}

export function pushEventFeed(eventType, items = []) {
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
}

export function pushCaptionFeedLine(text, options = {}) {
    const latestLine = elements.captionFeed.firstElementChild;
    if (latestLine?.dataset.feedKind === "caption" && latestLine.dataset.feedValue === text) {
        return;
    }

    const finalizeReason = options.finalizeReason ?? "live_final";
    if (
        latestLine?.dataset.feedKind === "caption" &&
        latestLine.dataset.mergeOpen === "true" &&
        shouldMergeCaptionFeedLine(
            latestLine.dataset.feedValue ?? "",
            text,
            finalizeReason,
        )
    ) {
        const mergedText = `${latestLine.dataset.feedValue ?? ""} ${text}`
            .replace(/\s+/gu, " ")
            .trim();
        latestLine.textContent = mergedText;
        latestLine.dataset.feedValue = mergedText;
        latestLine.dataset.mergeOpen = String(
            shouldKeepCaptionFeedOpen(mergedText, finalizeReason),
        );
        return;
    }

    const line = document.createElement("div");
    line.className = "feed-line";
    line.textContent = text;
    line.dataset.feedKind = "caption";
    line.dataset.feedValue = text;
    line.dataset.mergeOpen = String(
        shouldKeepCaptionFeedOpen(text, finalizeReason),
    );
    elements.captionFeed.prepend(line);
    trimFeed();
}
