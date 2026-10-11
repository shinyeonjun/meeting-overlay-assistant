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
