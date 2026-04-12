import { fetchHealth as fetchSharedHealth } from "@caps-client-shared/api/health-api.js";

import { buildApiUrl } from "../config/runtime.js";

export function fetchHealth() {
    return fetchSharedHealth({
        buildApiUrl,
    });
}
