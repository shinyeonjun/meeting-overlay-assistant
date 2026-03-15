import { requestJson } from "./http-client.js";

function buildQuery(filters = {}) {
    const query = new URLSearchParams();

    for (const [key, value] of Object.entries(filters)) {
        if (value === undefined || value === null || value === "") {
            continue;
        }
        query.set(key, String(value));
    }

    const serialized = query.toString();
    return serialized ? `?${serialized}` : "";
}

export async function fetchHistoryTimeline({
    scope = "mine",
    accountId = null,
    contactId = null,
    contextThreadId = null,
    limit = 8,
} = {}) {
    return requestJson(
        `/api/v1/history/timeline${buildQuery({
            scope,
            account_id: accountId,
            contact_id: contactId,
            context_thread_id: contextThreadId,
            limit,
        })}`,
    );
}
