/** 웹 클라이언트에서 쓰는 공통 API 호출을 담당한다. */
import { fetchWorkspaceOverview as fetchSharedWorkspaceOverview } from "@caps-client-shared/api/workspace-api.js";

import { buildApiUrl } from "../config/runtime.js";

export function fetchWorkspaceOverview(options = {}) {
  return fetchSharedWorkspaceOverview({
    buildApiUrl,
    ...options,
  });
}
