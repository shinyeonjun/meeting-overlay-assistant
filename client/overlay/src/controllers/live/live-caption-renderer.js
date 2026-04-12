/** 오버레이에서 실시간 흐름의 live caption renderer 제어를 담당한다. */
import { elements } from "../../dom/elements.js";
import { appState } from "../../state/app-state.js";
import { pushCaptionFeedLine } from "./live-feed.js";

const EMPTY_LIVE_TEXT = "아직 들어온 발화가 없습니다.";
const RECENT_CAPTION_FALLBACK = "최근 자막이 들어오면 여기에 누적됩니다.";

let renderedSegmentId = null;
let renderedText = "";

function isDraftUtterance(utterance) {
    return utterance.stability === "low" || (utterance.isPartial && utterance.kind === "preview");
}

function isSettlingUtterance(utterance) {
    return utterance.stability === "medium" || utterance.kind === "live_final";
}

function resolveVisualState(utterance) {
    if (!utterance?.text) {
        return "idle";
    }
    if (isDraftUtterance(utterance)) {
        return "draft";
    }
    if (isSettlingUtterance(utterance)) {
        return "settling";
    }
    return "final";
}

function applyVisualState(state) {
    if (!elements.liveText || !elements.statusDot) {
        return;
    }

    elements.liveText.classList.remove(
        "live-text--draft",
        "live-text--settling",
        "live-text--final",
    );
    elements.captionBox?.setAttribute("data-caption-state", state);

    if (state === "draft") {
        elements.liveText.classList.add("live-text--draft");
        elements.statusDot.className = "status-dot live";
        return;
    }

    if (state === "settling") {
        elements.liveText.classList.add("live-text--settling");
        elements.statusDot.className = "status-dot live";
        return;
    }

    if (state === "final") {
        elements.liveText.classList.add("live-text--final");
        elements.statusDot.className = "status-dot live";
        return;
    }

    elements.statusDot.className = "status-dot idle";
}

function renderUtteranceBadge(utterance) {
    if (!elements.liveConnectionStatus) {
        return;
    }

    if (!utterance?.text) {
        elements.liveConnectionStatus.textContent = "idle";
        elements.liveConnectionStatus.className = "badge idle";
        return;
    }

    elements.liveConnectionStatus.textContent = "capturing";
    elements.liveConnectionStatus.className = isDraftUtterance(utterance)
        ? "badge ready"
        : "badge live";
}

export function renderCurrentUtterance() {
    const utterance = appState.live.currentUtterance;

    if (!utterance) {
        elements.liveSpeaker.textContent = "";
        elements.liveText.textContent = EMPTY_LIVE_TEXT;
        applyVisualState("idle");
        renderUtteranceBadge(null);
        renderedSegmentId = null;
        renderedText = "";
        renderWorkspaceCaptionCompanion();
        return;
    }

    elements.captionBox?.classList.remove("collapsed");

    if (utterance.segmentId !== renderedSegmentId) {
        renderedSegmentId = utterance.segmentId;
        renderedText = "";
    }

    elements.liveSpeaker.textContent = utterance.speakerLabel ?? "";
    renderUtteranceBadge(utterance);

    if (renderedText !== utterance.text) {
        elements.liveText.textContent = utterance.text;
        renderedText = utterance.text;
    }

    applyVisualState(resolveVisualState(utterance));
    renderWorkspaceCaptionCompanion();
}

export function pushCompletedCaptionLine(line) {
    if (!line) {
        return;
    }

    pushCaptionFeedLine(line);
    renderWorkspaceCaptionCompanion();
}

function renderWorkspaceCaptionCompanion() {
    if (!elements.workspaceCaptionCurrent || !elements.workspaceCaptionRecent) {
        return;
    }

    const current = appState.live.currentUtterance;
    const history = appState.live.transcriptHistory ?? [];
    const recent = history.find((item) => item.id !== current?.id) ?? history[0] ?? null;

    elements.workspaceCaptionCurrent.textContent = formatCaptionLine(current) || EMPTY_LIVE_TEXT;
    elements.workspaceCaptionRecent.textContent = formatCaptionLine(recent) || RECENT_CAPTION_FALLBACK;
}

function formatCaptionLine(utterance) {
    if (!utterance?.text) {
        return "";
    }

    const speaker = utterance.speakerLabel ?? utterance.speaker_label ?? "";
    return speaker ? `${speaker}: ${utterance.text}` : utterance.text;
}
