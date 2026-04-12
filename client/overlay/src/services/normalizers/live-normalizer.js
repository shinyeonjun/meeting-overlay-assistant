/** 오버레이에서 공통 관련 live normalizer 서비스를 제공한다. */
function normalizeUtteranceKind(kind) {
    if (kind === "partial") {
        return "preview";
    }
    if (kind === "fast_final") {
        return "live_final";
    }
    if (kind === "final") {
        return "archive_final";
    }
    if (kind === "late_final") {
        return "late_archive_final";
    }
    return kind ?? "archive_final";
}

export function normalizeStreamPayload(payload) {
    return {
        sessionId: payload.session_id,
        error: payload.error ?? null,
        utterances: (payload.utterances ?? []).map((utterance) => {
            const normalizedKind = normalizeUtteranceKind(utterance.kind);
            return {
                id: utterance.id,
                seq_num: utterance.seq_num,
                segment_id: utterance.segment_id ?? null,
                text: utterance.text ?? "",
                confidence: utterance.confidence ?? 0,
                start_ms: utterance.start_ms ?? null,
                end_ms: utterance.end_ms ?? null,
                speaker_label: utterance.speaker_label ?? "LIVE",
                is_partial: utterance.is_partial ?? (normalizedKind === "preview" || normalizedKind === "live_final"),
                input_source: utterance.input_source ?? null,
                kind: normalizedKind,
                stability: utterance.stability ?? null,
            };
        }),
        events: (payload.events ?? []).map((event) => ({
            id: event.id,
            type: event.type,
            title: event.title,
            evidence_text: event.evidence_text ?? "",
            state: event.state,
            source_utterance_id: event.source_utterance_id ?? null,
            speaker_label: event.speaker_label ?? null,
        })),
    };
}
