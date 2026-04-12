/** 웹 클라이언트에서 쓰는 공통 API 호출을 담당한다. */
import { fetchHealth as fetchSharedHealth } from "@caps-client-shared/api/health-api.js";

import { buildApiUrl } from "../config/runtime.js";

export function fetchHealth() {
    return fetchSharedHealth({
        buildApiUrl,
    });
}
