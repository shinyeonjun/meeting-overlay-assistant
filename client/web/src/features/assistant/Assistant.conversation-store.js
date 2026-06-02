import {
  chatAssistant,
  fetchAssistantConversation,
} from "../../services/assistant-api.js";
import {
  ASSISTANT_POLL_MAX_FAILURES,
  buildChatRequest,
  buildMessagesFromConversationResponse,
  hasPendingAssistantResponse,
  loadConversationState,
  saveConversationState,
  shouldStopAssistantPollingAfterFailure,
} from "./Assistant.helpers.js";

const pendingRequestsByScope = new Map();
const pollersByScope = new Map();
const listenersByScope = new Map();
const POLL_INTERVAL_MS = 1500;

export function getAssistantConversationSnapshot(scopeKey) {
  return {
    scopeKey,
    ...loadConversationState(scopeKey),
    searching: pendingRequestsByScope.has(scopeKey) || pollersByScope.has(scopeKey),
  };
}

export function subscribeAssistantConversation(scopeKey, listener) {
  const listeners = listenersByScope.get(scopeKey) ?? new Set();
  listeners.add(listener);
  listenersByScope.set(scopeKey, listeners);
  listener(getAssistantConversationSnapshot(scopeKey));
  return () => {
    listeners.delete(listener);
    if (listeners.size === 0) {
      listenersByScope.delete(scopeKey);
    }
  };
}

export function submitAssistantQuery({ scopeKey, searchScope, query }) {
  const normalized = query.trim();
  if (!normalized || pendingRequestsByScope.has(scopeKey)) {
    return;
  }

  const { conversationId, requestHistory } = persistSubmittedUserMessage({
    scopeKey,
    query: normalized,
  });
  notifyConversation(scopeKey);

  const request = chatAssistant(
    buildChatRequest(normalized, searchScope, {
      conversationId,
      messages: requestHistory,
    }),
  )
    .then((response) => {
      persistAssistantResponse({ scopeKey, response });
    })
    .catch((error) => {
      persistAssistantError({ scopeKey, error });
    })
    .finally(() => {
      pendingRequestsByScope.delete(scopeKey);
      notifyConversation(scopeKey);
    });

  pendingRequestsByScope.set(scopeKey, request);
  notifyConversation(scopeKey);
}

function persistSubmittedUserMessage({ scopeKey, query }) {
  const currentState = {
    scopeKey,
    ...loadConversationState(scopeKey),
  };
  const requestHistory = currentState.messages;
  saveConversationState(scopeKey, {
    ...currentState,
    messages: [...currentState.messages, buildUserMessage(query)],
  });
  return {
    conversationId: currentState.conversationId,
    requestHistory,
  };
}

function persistAssistantResponse({ scopeKey, response }) {
  const latestState = {
    scopeKey,
    ...loadConversationState(scopeKey),
  };
  const conversationId = response.conversation_id ?? latestState.conversationId;
  if (response.status === "pending") {
    saveConversationState(scopeKey, {
      ...latestState,
      conversationId,
    });
    ensureConversationPolling({ scopeKey, conversationId });
    return;
  }
  saveConversationState(scopeKey, {
    ...latestState,
    conversationId,
    messages: [...latestState.messages, buildAssistantMessage(response)],
  });
}

function persistAssistantError({ scopeKey, error }) {
  const latestState = {
    scopeKey,
    ...loadConversationState(scopeKey),
  };
  saveConversationState(scopeKey, {
    ...latestState,
    messages: [...latestState.messages, buildAssistantErrorMessage(error)],
  });
}

export async function refreshAssistantConversation({ scopeKey, conversationId }) {
  const normalizedConversationId = String(conversationId ?? "").trim();
  if (!normalizedConversationId || pendingRequestsByScope.has(scopeKey)) {
    return;
  }

  try {
    const response = await fetchAssistantConversation({
      conversationId: normalizedConversationId,
    });
    const serverMessages = buildMessagesFromConversationResponse(response);
    const hasPendingResponse = hasPendingAssistantResponse(response);
    const currentState = {
      scopeKey,
      ...loadConversationState(scopeKey),
    };
    const currentPoller = pollersByScope.get(scopeKey);
    if (currentPoller?.conversationId === normalizedConversationId) {
      currentPoller.failureCount = 0;
    }
    if (serverMessages.length) {
      saveConversationState(scopeKey, {
        ...currentState,
        conversationId: response.conversation_id ?? currentState.conversationId,
        messages: serverMessages,
      });
    }
    if (hasPendingResponse) {
      ensureConversationPolling({
        scopeKey,
        conversationId: response.conversation_id ?? normalizedConversationId,
      });
    } else {
      stopConversationPolling(scopeKey);
    }
    notifyConversation(scopeKey);
  } catch (error) {
    handleConversationPollingFailure({ scopeKey, error });
  }
}

function notifyConversation(scopeKey) {
  const listeners = listenersByScope.get(scopeKey);
  if (!listeners?.size) {
    return;
  }
  const snapshot = getAssistantConversationSnapshot(scopeKey);
  listeners.forEach((listener) => listener(snapshot));
}

function buildUserMessage(content) {
  return {
    id: `user-${Date.now()}`,
    role: "user",
    content,
    createdAt: new Date().toISOString(),
  };
}

function buildAssistantMessage(response) {
  return {
    id: response.message_id ?? `assistant-${Date.now()}`,
    role: "assistant",
    content: response.answer,
    status: response.status ?? "completed",
    sources: response.sources ?? [],
    createdAt: new Date().toISOString(),
  };
}

function buildAssistantErrorMessage(
  error,
  fallbackMessage = "\uCC57\uBD07 \uC751\uB2F5\uC744 \uC0DD\uC131\uD558\uC9C0 \uBABB\uD588\uC2B5\uB2C8\uB2E4.",
) {
  return {
    id: `assistant-error-${Date.now()}`,
    role: "assistant",
    content: "",
    error: error instanceof Error ? error.message : fallbackMessage,
    createdAt: new Date().toISOString(),
  };
}

function ensureConversationPolling({ scopeKey, conversationId }) {
  const normalizedConversationId = String(conversationId ?? "").trim();
  if (!normalizedConversationId) {
    return;
  }
  const currentPoller = pollersByScope.get(scopeKey);
  if (currentPoller?.conversationId === normalizedConversationId) {
    return;
  }
  stopConversationPolling(scopeKey, { notify: false });
  const poller = {
    conversationId: normalizedConversationId,
    failureCount: 0,
    timerId: null,
  };
  pollersByScope.set(scopeKey, poller);
  scheduleConversationPoll(scopeKey);
  notifyConversation(scopeKey);
}

function scheduleConversationPoll(scopeKey) {
  const poller = pollersByScope.get(scopeKey);
  if (!poller) {
    return;
  }
  poller.timerId = globalThis.setTimeout(async () => {
    await refreshAssistantConversation({
      scopeKey,
      conversationId: poller.conversationId,
    });
    if (pollersByScope.has(scopeKey)) {
      scheduleConversationPoll(scopeKey);
    }
  }, POLL_INTERVAL_MS);
}

function handleConversationPollingFailure({ scopeKey, error }) {
  const poller = pollersByScope.get(scopeKey);
  if (!poller) {
    return;
  }
  poller.failureCount = (poller.failureCount ?? 0) + 1;
  if (!shouldStopAssistantPollingAfterFailure(
    poller.failureCount,
    ASSISTANT_POLL_MAX_FAILURES,
  )) {
    return;
  }
  const latestState = {
    scopeKey,
    ...loadConversationState(scopeKey),
  };
  saveConversationState(scopeKey, {
    ...latestState,
    messages: [...latestState.messages, buildAssistantErrorMessage(error)],
  });
  stopConversationPolling(scopeKey, { notify: false });
  notifyConversation(scopeKey);
}

function stopConversationPolling(scopeKey, options = {}) {
  const poller = pollersByScope.get(scopeKey);
  if (!poller) {
    return;
  }
  if (poller.timerId) {
    globalThis.clearTimeout(poller.timerId);
  }
  pollersByScope.delete(scopeKey);
  if (options.notify !== false) {
    notifyConversation(scopeKey);
  }
}
