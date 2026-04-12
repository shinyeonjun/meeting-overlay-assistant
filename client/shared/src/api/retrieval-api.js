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

export async function searchRetrieval({
    buildApiUrl,
    query,
    fetchImpl = fetch,
    accountId,
    contactId,
    contextThreadId,
    limit = 10,
}) {
    const queryString = buildQueryString({
        q: query,
        account_id: accountId,
        contact_id: contactId,
        context_thread_id: contextThreadId,
        limit,
    });
    const response = await fetchImpl(buildApiUrl(`/api/v1/retrieval/search${queryString}`));
    if (!response.ok) {
        throw new Error(`retrieval search 요청 실패: ${response.status}`);
    }
    return response.json();
}
