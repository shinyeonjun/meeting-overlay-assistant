import { elements } from "../../dom/elements.js";
import { appState } from "../../state/app-state.js";
import { pushCaptionFeedLine } from "./live-feed.js";

const EMPTY_LIVE_TEXT = "아직 들어온 발화가 없습니다.";
const RECENT_CAPTION_FALLBACK = "최근 자막이 들어오면 여기에 누적됩니다.";
const TYPEWRITER_CHAR_MS = 35;

let renderedSegmentId = null;
let renderedText = "";
let typewriterTimer = null;

function cancelTypewriter() {
    if (typewriterTimer !== null) {
        clearInterval(typewriterTimer);
        typewriterTimer = null;
    }
}

function typewriteText(textElement, currentText, newText) {
    cancelTypewriter();

    if (newText.startsWith(currentText) && newText.length > currentText.length) {
        const charsToAdd = newText.slice(currentText.length);
        let charIndex = 0;

        typewriterTimer = setInterval(() => {
            if (charIndex >= charsToAdd.length) {
                cancelTypewriter();
                return;
            }

            charIndex += 1;
            textElement.textContent = currentText + charsToAdd.slice(0, charIndex);
            renderedText = textElement.textContent;
        }, TYPEWRITER_CHAR_MS);
        return;
    }

    textElement.textContent = newText;
    renderedText = newText;
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

    if (utterance.stability === "low" || (utterance.isPartial && utterance.kind === "preview")) {
        elements.liveConnectionStatus.textContent = "preview";
        elements.liveConnectionStatus.className = "badge ready";
        return;
    }

    if (utterance.stability === "medium" || utterance.kind === "live_final") {
        elements.liveConnectionStatus.textContent = "live";
        elements.liveConnectionStatus.className = "badge live";
        return;
    }

    elements.liveConnectionStatus.textContent = "archive";
    elements.liveConnectionStatus.className = "badge idle";
}

export function renderCurrentUtterance() {
    const utterance = appState.live.currentUtterance;

    if (!utterance) {
        cancelTypewriter();
        elements.liveSpeaker.textContent = "";
        elements.liveText.textContent = EMPTY_LIVE_TEXT;
        elements.liveText.classList.remove("live-text--partial");
        elements.liveText.classList.remove("live-text--stable");
        renderUtteranceBadge(null);
        renderedSegmentId = null;
        renderedText = "";
        renderWorkspaceCaptionCompanion();
        return;
    }

    elements.captionBox?.classList.remove("collapsed");

    if (utterance.segmentId !== renderedSegmentId) {
        cancelTypewriter();
        renderedSegmentId = utterance.segmentId;
        renderedText = "";
    }

    elements.liveSpeaker.textContent = utterance.speakerLabel ?? "";
    renderUtteranceBadge(utterance);

    elements.liveText.classList.remove("live-text--partial");
    elements.liveText.classList.remove("live-text--stable");

    if (utterance.stability === "low" || (utterance.isPartial && utterance.kind === "preview")) {
        typewriteText(elements.liveText, renderedText, utterance.text);
        elements.liveText.classList.add("live-text--partial");
        renderWorkspaceCaptionCompanion();
        return;
    }

    if (utterance.stability === "medium" || utterance.kind === "live_final") {
        cancelTypewriter();
        elements.liveText.textContent = utterance.text;
        elements.liveText.classList.add("live-text--stable");
        renderedText = utterance.text;
        renderWorkspaceCaptionCompanion();
        return;
    }

    cancelTypewriter();
    elements.liveText.textContent = utterance.text;
    renderedText = utterance.text;
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
