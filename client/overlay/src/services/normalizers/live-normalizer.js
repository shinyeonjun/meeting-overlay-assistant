export function normalizeStreamPayload(payload) {
    return {
        sessionId: payload.session_id,
        error: payload.error ?? null,
        utterances: (payload.utterances ?? []).map((utterance) => ({
            id: utterance.id,
            seq_num: utterance.seq_num,
            segment_id: utterance.segment_id ?? null,
            text: utterance.text ?? "",
            confidence: utterance.confidence ?? 0,
            start_ms: utterance.start_ms ?? null,
            end_ms: utterance.end_ms ?? null,
            speaker_label: utterance.speaker_label ?? "LIVE",
            is_partial: utterance.is_partial ?? false,
            input_source: utterance.input_source ?? null,
            kind: utterance.kind ?? "final",
            stability: utterance.stability ?? null,
        })),
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
