function normalizeEventItem(item) {
    return {
        id: item.id,
        title: item.title,
        state: item.state,
        speaker_label: item.speaker_label ?? null,
    };
}

function normalizeManagedEventItem(item) {
    return {
        id: item.id,
        sessionId: item.session_id,
        eventType: item.event_type,
        title: item.title,
        body: item.body ?? "",
        evidenceText: item.evidence_text ?? "",
        speakerLabel: item.speaker_label ?? null,
        state: item.state,
        sourceUtteranceId: item.source_utterance_id ?? null,
        createdAtMs: item.created_at_ms ?? null,
        updatedAtMs: item.updated_at_ms ?? null,
    };
}

export function normalizeOverviewPayload(payload) {
    return {
        session: payload.session,
        currentTopic: payload.current_topic ?? null,
        questions: (payload.questions ?? []).map(normalizeEventItem),
        decisions: (payload.decisions ?? []).map(normalizeEventItem),
        actionItems: (payload.action_items ?? []).map(normalizeEventItem),
        risks: (payload.risks ?? []).map(normalizeEventItem),
    };
}

export function normalizeEventListPayload(payload) {
    return (payload.items ?? []).map(normalizeManagedEventItem);
}

export function normalizeEventPayload(payload) {
    return normalizeManagedEventItem(payload);
}
