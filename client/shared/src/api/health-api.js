/** 웹과 오버레이가 공유하는 공통 API 클라이언트를 제공한다. */
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
