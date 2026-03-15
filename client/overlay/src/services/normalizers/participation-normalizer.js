export function normalizeSessionParticipationPayload(payload) {
    return {
        sessionId: payload.session_id,
        participants: (payload.participants ?? []).map((item) => ({
            name: item.name,
            normalizedName: item.normalized_name ?? "",
            contactId: item.contact_id ?? null,
            accountId: item.account_id ?? null,
            email: item.email ?? "",
            jobTitle: item.job_title ?? "",
            department: item.department ?? "",
            resolutionStatus: item.resolution_status ?? "unmatched",
        })),
        participantCandidates: (payload.participant_candidates ?? []).map((item) => ({
            name: item.name,
            accountId: item.account_id ?? null,
            resolutionStatus: item.resolution_status ?? "unmatched",
            matchedContactCount: item.matched_contact_count ?? 0,
            matchedContacts: (item.matched_contacts ?? []).map((match) => ({
                contactId: match.contact_id,
                accountId: match.account_id ?? null,
                name: match.name ?? "",
                email: match.email ?? "",
                jobTitle: match.job_title ?? "",
                department: match.department ?? "",
            })),
        })),
        summary: {
            totalCount: payload.summary?.total_count ?? 0,
            linkedCount: payload.summary?.linked_count ?? 0,
            unmatchedCount: payload.summary?.unmatched_count ?? 0,
            ambiguousCount: payload.summary?.ambiguous_count ?? 0,
            unresolvedCount: payload.summary?.unresolved_count ?? 0,
            pendingFollowupCount: payload.summary?.pending_followup_count ?? 0,
            resolvedFollowupCount: payload.summary?.resolved_followup_count ?? 0,
        },
    };
}

export function normalizeParticipantFollowupListPayload(payload) {
    return (payload.items ?? []).map((item) => ({
        id: item.id,
        sessionId: item.session_id,
        participantOrder: item.participant_order,
        participantName: item.participant_name,
        resolutionStatus: item.resolution_status,
        followupStatus: item.followup_status,
        matchedContactCount: item.matched_contact_count ?? 0,
        contactId: item.contact_id ?? null,
        accountId: item.account_id ?? null,
        createdAt: item.created_at,
        updatedAt: item.updated_at,
        resolvedAt: item.resolved_at ?? null,
        resolvedByUserId: item.resolved_by_user_id ?? null,
    }));
}
