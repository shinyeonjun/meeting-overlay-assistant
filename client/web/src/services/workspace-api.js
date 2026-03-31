import { fetchWorkspaceOverview as fetchSharedWorkspaceOverview } from "@caps-client-shared/api/workspace-api.js";

import { buildApiUrl } from "../config/runtime.js";

export function fetchWorkspaceOverview(options = {}) {
  return fetchSharedWorkspaceOverview({
    buildApiUrl,
    ...options,
  });
}
