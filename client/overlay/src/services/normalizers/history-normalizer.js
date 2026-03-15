function normalizeCarryOverItem(item) {
    return {
        eventId: item.event_id,
        sessionId: item.session_id,
        sessionTitle: item.session_title,
        eventType: item.event_type,
        title: item.title,
        state: item.state,
        updatedAtMs: item.updated_at_ms ?? 0,
    };
}

function normalizeRetrievalBriefItem(item) {
    return {
        chunkId: item.chunk_id,
        documentId: item.document_id,
        sourceType: item.source_type,
        sourceId: item.source_id,
        documentTitle: item.document_title,
        chunkText: item.chunk_text,
        chunkHeading: item.chunk_heading ?? null,
        distance: item.distance ?? 0,
        sessionId: item.session_id ?? null,
        reportId: item.report_id ?? null,
        accountId: item.account_id ?? null,
        contactId: item.contact_id ?? null,
        contextThreadId: item.context_thread_id ?? null,
    };
}

export function normalizeHistoryTimelinePayload(payload) {
    return {
        accountId: payload.account_id ?? null,
        contactId: payload.contact_id ?? null,
        contextThreadId: payload.context_thread_id ?? null,
        sessionCount: payload.session_count ?? 0,
        reportCount: payload.report_count ?? 0,
        sessions: (payload.sessions ?? []).map((item) => ({
            id: item.id,
            title: item.title,
            status: item.status,
            primaryInputSource: item.primary_input_source ?? null,
            startedAt: item.started_at,
            accountId: item.account_id ?? null,
            contactId: item.contact_id ?? null,
            contextThreadId: item.context_thread_id ?? null,
        })),
        reports: (payload.reports ?? []).map((item) => ({
            id: item.id,
            sessionId: item.session_id,
            reportType: item.report_type,
            version: item.version,
            generatedAt: item.generated_at,
            filePath: item.file_path,
            insightSource: item.insight_source,
        })),
        carryOver: {
            decisions: (payload.carry_over?.decisions ?? []).map(normalizeCarryOverItem),
            actionItems: (payload.carry_over?.action_items ?? []).map(normalizeCarryOverItem),
            risks: (payload.carry_over?.risks ?? []).map(normalizeCarryOverItem),
            questions: (payload.carry_over?.questions ?? []).map(normalizeCarryOverItem),
        },
        retrievalBrief: {
            query: payload.retrieval_brief?.query ?? null,
            resultCount: payload.retrieval_brief?.result_count ?? 0,
            items: (payload.retrieval_brief?.items ?? []).map(normalizeRetrievalBriefItem),
        },
    };
}
