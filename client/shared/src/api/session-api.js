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

export async function fetchSessions({
    buildApiUrl,
    fetchImpl = fetch,
    scope = "mine",
    accountId,
    contactId,
    contextThreadId,
    limit = 20,
}) {
    const queryString = buildQueryString({
        scope,
        account_id: accountId,
        contact_id: contactId,
        context_thread_id: contextThreadId,
        limit,
    });
    const response = await fetchImpl(buildApiUrl(`/api/v1/sessions${queryString}`));
    if (!response.ok) {
        throw new Error(`sessions 요청 실패: ${response.status}`);
    }
    return response.json();
}

export async function fetchSessionOverview({
    buildApiUrl,
    sessionId,
    fetchImpl = fetch,
}) {
    const response = await fetchImpl(buildApiUrl(`/api/v1/sessions/${sessionId}/overview`));
    if (!response.ok) {
        throw new Error(`session overview 요청 실패: ${response.status}`);
    }
    return response.json();
}

export async function fetchSessionTranscript({
    buildApiUrl,
    sessionId,
    fetchImpl = fetch,
}) {
    const response = await fetchImpl(buildApiUrl(`/api/v1/sessions/${sessionId}/transcript`));
    if (!response.ok) {
        throw new Error(`session transcript 요청 실패: ${response.status}`);
    }
    return response.json();
}
