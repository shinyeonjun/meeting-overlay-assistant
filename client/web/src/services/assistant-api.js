import {
  chatAssistant as chatSharedAssistant,
  deleteAssistantConversation as deleteSharedAssistantConversation,
  fetchAssistantConversation as fetchSharedAssistantConversation,
  fetchAssistantConversations as fetchSharedAssistantConversations,
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

export function fetchAssistantConversations(options) {
  return fetchSharedAssistantConversations({
    buildApiUrl,
    ...options,
  });
}

export function deleteAssistantConversation(options) {
  return deleteSharedAssistantConversation({
    buildApiUrl,
    ...options,
  });
}
