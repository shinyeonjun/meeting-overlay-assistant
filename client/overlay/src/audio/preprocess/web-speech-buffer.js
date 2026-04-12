/** 오버레이 런타임의 web speech buffer 모듈이다. */
const FINAL_DEDUP_WINDOW_MS = 1000;

export function createWebSpeechBuffer() {
    return {
        seqNum: 0,
        revision: 0,
        segmentId: null,
        lastInterim: "",
        pendingFinalTexts: [],
        lastFinalText: "",
        lastFinalSentAt: 0,
    };
}

export function resetWebSpeechBuffer(buffer) {
    buffer.seqNum = 0;
    buffer.revision = 0;
    buffer.segmentId = null;
    buffer.lastInterim = "";
    buffer.pendingFinalTexts = [];
    buffer.lastFinalText = "";
    buffer.lastFinalSentAt = 0;
}

export function buildWebSpeechPartialPayload(buffer, { sessionId, text, source, nowMs = Date.now() }) {
    const normalized = text.trim();
    if (!normalized || normalized === buffer.lastInterim || !sessionId) {
        return null;
    }

    if (buffer.segmentId === null) {
        buffer.seqNum += 1;
        buffer.revision = 0;
        buffer.segmentId = `seg-webspeech-${buffer.seqNum}`;
    }

    buffer.revision += 1;
    buffer.lastInterim = normalized;

    return {
        type: "payload",
        payload: {
            session_id: sessionId,
            utterances: [
                {
                    id: `live-webspeech-${buffer.seqNum}-${buffer.revision}`,
                    seq_num: buffer.seqNum,
                    segment_id: buffer.segmentId,
                    text: normalized,
                    confidence: 0.7,
                    start_ms: nowMs,
                    end_ms: nowMs,
                    is_partial: true,
                    kind: "partial",
                    revision: buffer.revision,
                    input_source: source,
                },
            ],
            events: [],
            error: null,
        },
    };
}

export function queueWebSpeechFinalText(buffer, text, nowMs = Date.now()) {
    const normalized = text.trim();
    if (!normalized) {
        return false;
    }

    if (
        normalized === buffer.lastFinalText
        && nowMs - buffer.lastFinalSentAt < FINAL_DEDUP_WINDOW_MS
    ) {
        return false;
    }

    buffer.lastFinalText = normalized;
    buffer.lastFinalSentAt = nowMs;
    buffer.pendingFinalTexts.push(normalized);
    buffer.segmentId = null;
    buffer.revision = 0;
    buffer.lastInterim = "";
    return true;
}

export function drainWebSpeechFinalTexts(buffer, socket) {
    if (!socket || socket.readyState !== WebSocket.OPEN) {
        return;
    }

    while (buffer.pendingFinalTexts.length > 0) {
        const line = buffer.pendingFinalTexts.shift();
        if (line) {
            socket.send(line);
        }
    }
}
