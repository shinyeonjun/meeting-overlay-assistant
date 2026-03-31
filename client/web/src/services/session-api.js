import {
  fetchSessionOverview as fetchSharedSessionOverview,
} from "@caps-client-shared/api/session-api.js";
import { fetchSessionDetail as fetchSharedSessionDetail } from "@caps-client-shared/api/session-detail-api.js";

import { buildApiUrl } from "../config/runtime.js";

export function fetchSessionDetail(options) {
  return fetchSharedSessionDetail({
    buildApiUrl,
    ...options,
  });
}

export function fetchSessionOverview(options) {
  return fetchSharedSessionOverview({
    buildApiUrl,
    ...options,
  });
}
