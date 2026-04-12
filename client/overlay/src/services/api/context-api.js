/** 오버레이에서 공통 관련 context api 서비스를 제공한다. */
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

export async function listAccounts({ limit = 100 } = {}) {
    return requestJson(`/api/v1/context/accounts${buildQuery({ limit })}`);
}

export async function listContacts({ accountId = null, limit = 100 } = {}) {
    return requestJson(`/api/v1/context/contacts${buildQuery({ account_id: accountId, limit })}`);
}

export async function listContextThreads({ accountId = null, contactId = null, limit = 100 } = {}) {
    return requestJson(
        `/api/v1/context/threads${buildQuery({
            account_id: accountId,
            contact_id: contactId,
            limit,
        })}`,
    );
}
