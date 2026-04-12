/** 오버레이에서 공통 관련 context normalizer 서비스를 제공한다. */
function normalizeAccountItem(item) {
    return {
        id: item.id,
        workspaceId: item.workspace_id,
        name: item.name,
        description: item.description ?? "",
        status: item.status,
        createdByUserId: item.created_by_user_id ?? null,
        createdAt: item.created_at,
        updatedAt: item.updated_at,
    };
}

function normalizeContactItem(item) {
    return {
        id: item.id,
        workspaceId: item.workspace_id,
        accountId: item.account_id ?? null,
        name: item.name,
        email: item.email ?? "",
        jobTitle: item.job_title ?? "",
        notes: item.notes ?? "",
        status: item.status,
        createdByUserId: item.created_by_user_id ?? null,
        createdAt: item.created_at,
        updatedAt: item.updated_at,
    };
}

function normalizeContextThreadItem(item) {
    return {
        id: item.id,
        workspaceId: item.workspace_id,
        accountId: item.account_id ?? null,
        contactId: item.contact_id ?? null,
        title: item.title,
        summary: item.summary ?? "",
        status: item.status,
        createdByUserId: item.created_by_user_id ?? null,
        createdAt: item.created_at,
        updatedAt: item.updated_at,
    };
}

export function normalizeAccountListPayload(payload) {
    return (payload.items ?? []).map(normalizeAccountItem);
}

export function normalizeContactListPayload(payload) {
    return (payload.items ?? []).map(normalizeContactItem);
}

export function normalizeContextThreadListPayload(payload) {
    return (payload.items ?? []).map(normalizeContextThreadItem);
}
