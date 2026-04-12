function buildQueryString(params) {
    const searchParams = new URLSearchParams();
    for (const [key, value] of Object.entries(params)) {
        if (value === undefined || value === null || value === "") {
            continue;
        }
        searchParams.set(key, String(value));
    }
    const encoded = searchParams.toString();
    return encoded ? `?${encoded}` : "";
}

export async function fetchWorkspaceOverview({
    buildApiUrl,
    fetchImpl = fetch,
    scope = "mine",
    accountId,
    contactId,
    contextThreadId,
    limit = 8,
    includeReports = true,
    includeCarryOver = true,
    includeRetrievalBrief = true,
}) {
    const queryString = buildQueryString({
        scope,
        account_id: accountId,
        contact_id: contactId,
        context_thread_id: contextThreadId,
        limit,
        include_reports: includeReports,
        include_carry_over: includeCarryOver,
        include_retrieval_brief: includeRetrievalBrief,
    });
    const response = await fetchImpl(buildApiUrl(`/api/v1/workspace/overview${queryString}`));
    if (!response.ok) {
        throw new Error(`workspace overview 요청 실패: ${response.status}`);
    }
    return response.json();
}
