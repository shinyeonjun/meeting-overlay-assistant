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

export async function fetchRecentReports({
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
    const path = queryString ? `/api/v1/reports/${queryString}` : "/api/v1/reports/";
    const response = await fetchImpl(buildApiUrl(path));
    if (!response.ok) {
        throw new Error(`recent reports 요청 실패: ${response.status}`);
    }
    return response.json();
}

export async function fetchReportDetail({
    buildApiUrl,
    sessionId,
    reportId,
    fetchImpl = fetch,
}) {
    const response = await fetchImpl(buildApiUrl(`/api/v1/reports/${sessionId}/${reportId}`));
    if (!response.ok) {
        throw new Error(`report detail 요청 실패: ${response.status}`);
    }
    return response.json();
}

export async function fetchLatestReport({
    buildApiUrl,
    sessionId,
    fetchImpl = fetch,
}) {
    const response = await fetchImpl(buildApiUrl(`/api/v1/reports/${sessionId}/latest`));
    if (!response.ok) {
        throw new Error(`latest report 요청 실패: ${response.status}`);
    }
    return response.json();
}

export async function fetchFinalReportStatus({
    buildApiUrl,
    sessionId,
    fetchImpl = fetch,
}) {
    const response = await fetchImpl(buildApiUrl(`/api/v1/reports/${sessionId}/final-status`));
    if (!response.ok) {
        throw new Error(`final report status 요청 실패: ${response.status}`);
    }
    return response.json();
}

export async function enqueueReportGenerationJob({
    buildApiUrl,
    sessionId,
    fetchImpl = fetch,
}) {
    const response = await fetchImpl(buildApiUrl(`/api/v1/reports/${sessionId}/job`), {
        method: "POST",
    });
    if (!response.ok) {
        throw new Error(`report job 생성 요청 실패: ${response.status}`);
    }
    return response.json();
}

export async function fetchReportGenerationJob({
    buildApiUrl,
    sessionId,
    fetchImpl = fetch,
}) {
    const response = await fetchImpl(buildApiUrl(`/api/v1/reports/${sessionId}/job`));
    if (!response.ok) {
        throw new Error(`report job 조회 실패: ${response.status}`);
    }
    return response.json();
}

export function buildReportArtifactUrl({
    buildApiUrl,
    sessionId,
    reportId,
    artifactKind = "source",
    download = false,
}) {
    const queryString = buildQueryString({ download: download ? "true" : "" });
    return buildApiUrl(
        `/api/v1/reports/${sessionId}/${reportId}/artifact/${artifactKind}${queryString}`,
    );
}
