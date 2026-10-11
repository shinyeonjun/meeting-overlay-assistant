function buildQueryString(params) {
    const searchParams = new URLSearchParams();
    for (const [key, value] of Object.entries(params)) {
        if (value === undefined || value === null || value === "") {
            continue;
        }
        searchParams.set(key, String(value));
    }
    const encoded = searchParams.toString();
    return encoded ? `?${encoded}` : "";
}

