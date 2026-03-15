import { requestJson } from "./http-client.js";

export async function createSession({
    title,
    primaryInputSource,
    accountId = null,
    contactId = null,
    contextThreadId = null,
    participants = [],
}) {
    return requestJson("/api/v1/sessions", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
            title,
            mode: "meeting",
            primary_input_source: primaryInputSource,
            account_id: accountId,
            contact_id: contactId,
            context_thread_id: contextThreadId,
            participants,
        }),
    });
}

export async function endSession(sessionId) {
    return requestJson(`/api/v1/sessions/${sessionId}/end`, {
        method: "POST",
    });
}

export async function startSession(sessionId) {
    return requestJson(`/api/v1/sessions/${sessionId}/start`, {
        method: "POST",
    });
}

export async function fetchOverview(sessionId) {
    return requestJson(`/api/v1/sessions/${sessionId}/overview`);
}

export async function listSessions({
    scope = "mine",
    limit = 12,
    accountId = null,
    contactId = null,
    contextThreadId = null,
} = {}) {
    const query = new URLSearchParams({
        scope,
        limit: String(limit),
    });
    if (accountId) {
        query.set("account_id", accountId);
    }
    if (contactId) {
        query.set("contact_id", contactId);
    }
    if (contextThreadId) {
        query.set("context_thread_id", contextThreadId);
    }
    return requestJson(`/api/v1/sessions/?${query.toString()}`);
}
