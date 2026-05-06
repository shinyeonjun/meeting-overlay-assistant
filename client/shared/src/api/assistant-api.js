export async function chatAssistant({
    buildApiUrl,
    query,
    fetchImpl = fetch,
    sourceTypes,
    sessionId,
    accountId,
    contactId,
    contextThreadId,
    limit = 8,
}) {
    const response = await fetchImpl(buildApiUrl("/api/v1/assistant/chat"), {
        method: "POST",
        headers: {
            "Content-Type": "application/json",
        },
        body: JSON.stringify({
            query,
            source_types: sourceTypes,
            session_id: sessionId,
            account_id: accountId,
            contact_id: contactId,
            context_thread_id: contextThreadId,
            limit,
        }),
    });
    if (!response.ok) {
        throw new Error(`assistant chat 요청 실패: ${response.status}`);
    }
    return response.json();
}
