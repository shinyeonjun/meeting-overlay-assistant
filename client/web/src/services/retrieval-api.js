import { searchRetrieval as searchSharedRetrieval } from "@caps-client-shared/api/retrieval-api.js";

import { buildApiUrl } from "../config/runtime.js";

export function searchRetrieval(options) {
  return searchSharedRetrieval({
    buildApiUrl,
    ...options,
  });
}
