const TERMINAL_ENDING_PATTERN =
    /(?:[.?!]|죠|요|네요|인데요|입니다|습니다|이에요|예요|거예요|군요)$/u;

export const CAPTION_FEED_MERGE_MAX_COMPACT_CHARS = 46;
export const CAPTION_SILENCE_FINALIZE_MAX_COMPACT_CHARS = 80;

function compactLength(text) {
    return (text ?? "").replace(/\s+/gu, "").length;
}

export function looksLikeTerminalCaptionText(text) {
    const normalized = text?.trim() ?? "";
    if (!normalized) {
        return false;
    }
    return TERMINAL_ENDING_PATTERN.test(normalized);
}

export function isNonTerminalSilenceFinalize(line, metrics) {
    if (!line || metrics?.finalizeReason !== "silence") {
        return false;
    }
    return !looksLikeTerminalCaptionText(line);
}

export function isWeakSilenceFragment(line, metrics, minCompactChars = 12) {
    if (!isNonTerminalSilenceFinalize(line, metrics)) {
        return false;
    }

    return compactLength(line) <= minCompactChars;
}

export function shouldSuppressSilenceFinalizeCommit(line, metrics) {
    if (!line || metrics?.finalizeReason !== "silence") {
        return false;
    }

    if (isNonTerminalSilenceFinalize(line, metrics)) {
        return true;
    }

    return compactLength(line) > CAPTION_SILENCE_FINALIZE_MAX_COMPACT_CHARS;
}

export function shouldKeepCaptionFeedOpen(text, finalizeReason) {
    if (!text || finalizeReason !== "live_final") {
        return false;
    }

    if (looksLikeTerminalCaptionText(text)) {
        return false;
    }

    return compactLength(text) < CAPTION_FEED_MERGE_MAX_COMPACT_CHARS;
}

export function shouldMergeCaptionFeedLine(previousText, nextText, finalizeReason) {
    if (!previousText || !nextText || finalizeReason !== "live_final") {
        return false;
    }

    if (!shouldKeepCaptionFeedOpen(previousText, finalizeReason)) {
        return false;
    }

    const mergedText = `${previousText} ${nextText}`.replace(/\s+/gu, " ").trim();
    return compactLength(mergedText) <= CAPTION_FEED_MERGE_MAX_COMPACT_CHARS;
}
