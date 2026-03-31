export async function fetchHealth({
    buildApiUrl,
    fetchImpl = fetch,
}) {
    const response = await fetchImpl(buildApiUrl("/health"));
    if (!response.ok) {
        throw new Error(`health 요청 실패: ${response.status}`);
    }
    return response.json();
}
