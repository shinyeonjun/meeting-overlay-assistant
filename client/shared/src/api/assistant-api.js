export async function chatAssistant({
    buildApiUrl,
    query,
    conversationId,
    history,
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
            conversation_id: conversationId,
            history,
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

export async function fetchAssistantConversation({
    buildApiUrl,
    conversationId,
    fetchImpl = fetch,
}) {
    const response = await fetchImpl(
        buildApiUrl(`/api/v1/assistant/conversations/${encodeURIComponent(conversationId)}`),
    );
    if (!response.ok) {
        throw new Error(`assistant conversation 요청 실패: ${response.status}`);
    }
    return response.json();
}

export async function fetchAssistantConversations({
    buildApiUrl,
    accountId,
    contactId,
    contextThreadId,
    fetchImpl = fetch,
    limit = 30,
}) {
    const params = new URLSearchParams();
    params.set("limit", String(limit));
    if (accountId) {
        params.set("account_id", accountId);
    }
    if (contactId) {
        params.set("contact_id", contactId);
    }
    if (contextThreadId) {
        params.set("context_thread_id", contextThreadId);
    }
    const response = await fetchImpl(
        buildApiUrl(`/api/v1/assistant/conversations?${params.toString()}`),
    );
    if (!response.ok) {
        throw new Error(`assistant conversation list request failed: ${response.status}`);
    }
    return response.json();
}

export async function deleteAssistantConversation({
    buildApiUrl,
    conversationId,
    fetchImpl = fetch,
}) {
    const response = await fetchImpl(
        buildApiUrl(`/api/v1/assistant/conversations/${encodeURIComponent(conversationId)}`),
        {
            method: "DELETE",
        },
    );
    if (!response.ok && response.status !== 404) {
        throw new Error(`assistant conversation delete request failed: ${response.status}`);
    }
    return { deleted: response.ok };
}
