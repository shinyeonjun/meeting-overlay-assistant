function normalizeWorkspaceUrl(rawValue, fallbackValue) {
    const trimmedValue = String(rawValue ?? "").trim();
    const candidate = trimmedValue || fallbackValue;

    try {
        return new URL(candidate).toString();
    } catch {
        return new URL(fallbackValue).toString();
    }
}

const defaultWorkspaceUrl = normalizeWorkspaceUrl(
    import.meta.env.VITE_WEB_WORKSPACE_URL,
    "http://127.0.0.1:1430",
);

export function buildWebWorkspaceUrl({
    sectionId = "overview",
    sessionId = null,
    serverBaseUrl = null,
} = {}) {
    const url = new URL(defaultWorkspaceUrl);

    if (sectionId) {
        url.searchParams.set("section", sectionId);
    }
    if (sessionId) {
        url.searchParams.set("sessionId", sessionId);
    }
    if (serverBaseUrl) {
        url.searchParams.set("serverBaseUrl", serverBaseUrl);
    }

    return url.toString();
}
