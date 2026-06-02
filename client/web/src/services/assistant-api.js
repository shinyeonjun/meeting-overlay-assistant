import {
  chatAssistant as chatSharedAssistant,
  fetchAssistantConversation as fetchSharedAssistantConversation,
} from "@caps-client-shared/api/assistant-api.js";

import { buildApiUrl } from "../config/runtime.js";

export function chatAssistant(options) {
  return chatSharedAssistant({
    buildApiUrl,
    ...options,
  });
}

export function fetchAssistantConversation(options) {
  return fetchSharedAssistantConversation({
    buildApiUrl,
    ...options,
  });
}
