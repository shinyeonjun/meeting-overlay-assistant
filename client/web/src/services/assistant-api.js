import { chatAssistant as chatSharedAssistant } from "@caps-client-shared/api/assistant-api.js";

import { buildApiUrl } from "../config/runtime.js";

export function chatAssistant(options) {
  return chatSharedAssistant({
    buildApiUrl,
    ...options,
  });
}
