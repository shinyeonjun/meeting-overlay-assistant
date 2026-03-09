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
        priority: item.priority ?? 0,
        assignee: item.assignee ?? "",
        dueDate: item.due_date ?? "",
        topicGroup: item.topic_group ?? "",
        sourceUtteranceId: item.source_utterance_id ?? null,
        sourceScreenId: item.source_screen_id ?? null,
        createdAtMs: item.created_at_ms ?? null,
        updatedAtMs: item.updated_at_ms ?? null,
        inputSource: item.input_source ?? null,
    };
}

export function normalizeSessionPayload(payload) {
    return {
        id: payload.id,
        title: payload.title,
        mode: payload.mode,
        source: payload.source,
        status: payload.status,
        startedAt: payload.started_at ?? null,
        endedAt: payload.ended_at ?? null,
        primaryInputSource: payload.primary_input_source ?? null,
        actualActiveSources: payload.actual_active_sources ?? [],
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
        })),
        events: (payload.events ?? []).map((event) => ({
            id: event.id,
            type: event.type,
            title: event.title,
            evidence_text: event.evidence_text ?? "",
            state: event.state,
            priority: event.priority ?? 0,
            speaker_label: event.speaker_label ?? null,
            assignee: event.assignee ?? null,
            due_date: event.due_date ?? null,
            input_source: event.input_source ?? null,
        })),
    };
}

export function normalizeEventListPayload(payload) {
    return (payload.items ?? []).map(normalizeManagedEventItem);
}

export function normalizeEventPayload(payload) {
    return normalizeManagedEventItem(payload);
}

export function normalizeRegenerateReportsPayload(payload) {
    return {
        sessionId: payload.session_id,
        items: (payload.items ?? []).map((item) => ({
            id: item.id,
            reportType: item.report_type,
            version: item.version ?? null,
            filePath: item.file_path,
        })),
    };
}

export function normalizeFinalReportStatusPayload(payload) {
    return {
        sessionId: payload.session_id,
        status: payload.status,
        reportCount: payload.report_count ?? 0,
        latestReportId: payload.latest_report_id ?? null,
        latestReportType: payload.latest_report_type ?? null,
        latestGeneratedAt: payload.latest_generated_at ?? null,
        latestFilePath: payload.latest_file_path ?? null,
    };
}
