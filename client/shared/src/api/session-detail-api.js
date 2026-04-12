export async function fetchSessionDetail({
    buildApiUrl,
    sessionId,
    fetchImpl = fetch,
}) {
    const response = await fetchImpl(buildApiUrl(`/api/v1/sessions/${sessionId}`));
    if (!response.ok) {
        throw new Error(`session detail 요청 실패: ${response.status}`);
    }
    return response.json();
}
