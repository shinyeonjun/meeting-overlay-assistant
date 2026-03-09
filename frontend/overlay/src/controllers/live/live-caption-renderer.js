import { elements } from "../../dom/elements.js";
import { appState } from "../../state/app-state.js";
import { pushCaptionFeedLine } from "./live-feed.js";

const EMPTY_LIVE_TEXT = "아직 들어온 발화가 없습니다.";
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

export function renderCurrentUtterance() {
    const utterance = appState.live.currentUtterance;

    if (!utterance) {
        cancelTypewriter();
        elements.liveSpeaker.textContent = "";
        elements.liveText.textContent = EMPTY_LIVE_TEXT;
        elements.liveText.classList.remove("live-text--partial");
        renderedSegmentId = null;
        renderedText = "";
        return;
    }

    elements.captionBox?.classList.remove("collapsed");

    if (utterance.segmentId !== renderedSegmentId) {
        cancelTypewriter();
        renderedSegmentId = utterance.segmentId;
        renderedText = "";
    }

    elements.liveSpeaker.textContent = utterance.speakerLabel ?? "";
    if (elements.liveConnectionStatus && utterance.text) {
        elements.liveConnectionStatus.textContent = `live: ${utterance.text.slice(0, 20)}`;
        elements.liveConnectionStatus.className = "badge live";
    }

    if (utterance.isPartial) {
        typewriteText(elements.liveText, renderedText, utterance.text);
        elements.liveText.classList.add("live-text--partial");
        return;
    }

    cancelTypewriter();
    elements.liveText.textContent = utterance.text;
    elements.liveText.classList.remove("live-text--partial");
    renderedText = utterance.text;
}

export function pushCompletedCaptionLine(line) {
    if (!line) {
        return;
    }
    pushCaptionFeedLine(line);
}
