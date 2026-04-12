/** 오버레이에서 공통 관련 session normalizer 서비스를 제공한다. */
export function normalizeSessionPayload(payload) {
    return {
        id: payload.id,
        title: payload.title,
        mode: payload.mode,
        status: payload.status,
        startedAt: payload.started_at ?? null,
        endedAt: payload.ended_at ?? null,
        accountId: payload.account_id ?? null,
        contactId: payload.contact_id ?? null,
        contextThreadId: payload.context_thread_id ?? null,
        participants: payload.participants ?? [],
        participantLinks: [],
        participantCandidates: [],
        participationSummary: payload.participant_summary ? {
            totalCount: payload.participant_summary.total_count ?? 0,
            linkedCount: payload.participant_summary.linked_count ?? 0,
            unmatchedCount: payload.participant_summary.unmatched_count ?? 0,
            ambiguousCount: payload.participant_summary.ambiguous_count ?? 0,
            unresolvedCount: payload.participant_summary.unresolved_count ?? 0,
            pendingFollowupCount: payload.participant_summary.pending_followup_count ?? 0,
            resolvedFollowupCount: payload.participant_summary.resolved_followup_count ?? 0,
        } : null,
        primaryInputSource: payload.primary_input_source ?? null,
        actualActiveSources: payload.actual_active_sources ?? [],
    };
}

export function normalizeSessionListPayload(payload) {
    return (payload.items ?? []).map(normalizeSessionPayload);
}
