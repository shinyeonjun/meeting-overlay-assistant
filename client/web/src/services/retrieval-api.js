/** 웹 클라이언트에서 쓰는 공통 API 호출을 담당한다. */
import { searchRetrieval as searchSharedRetrieval } from "@caps-client-shared/api/retrieval-api.js";

import { buildApiUrl } from "../config/runtime.js";

export function searchRetrieval(options) {
  return searchSharedRetrieval({
    buildApiUrl,
    ...options,
  });
}
