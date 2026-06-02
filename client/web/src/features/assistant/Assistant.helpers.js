export const SUGGESTED_QUESTIONS = [
  "지난 회의에서 결정된 건 뭐야?",
  "다음에 해야 할 일만 알려줘",
  "최근 회의에서 논의한 핵심만 정리해줘",
  "근거 원문도 같이 확인해줘",
];

const CONVERSATION_STORAGE_PREFIX = "caps.assistant.conversation.v1";
const MAX_STORED_MESSAGES = 40;
const MAX_HISTORY_MESSAGES = 8;
const MAX_HISTORY_CONTENT_CHARS = 700;
export const ASSISTANT_POLL_MAX_FAILURES = 20;

export function buildChatRequest(query, searchScope, conversationState = {}) {
  return {
    query,
    conversationId: conversationState.conversationId,
    history: buildChatHistory(conversationState.messages ?? []),
    limit: 4,
    sourceTypes: ["report", "note"],
    accountId: searchScope?.accountId,
    contactId: searchScope?.contactId,
    contextThreadId: searchScope?.contextThreadId,
  };
}

export function buildConversationScopeKey(searchScope = {}) {
  const ownerKey = searchScope?.userId ? `user:${searchScope.userId}` : "anonymous";
  const accountKey = searchScope?.accountId ?? "all-accounts";
  const contactKey = searchScope?.contactId ?? "all-contacts";
  const threadKey = searchScope?.contextThreadId ?? "workspace";
  return [ownerKey, accountKey, contactKey, threadKey].join("|");
}

export function buildMessagesFromConversationResponse(response) {
  if (!Array.isArray(response?.messages)) {
    return [];
  }
  return response.messages
    .filter((message) => message?.role === "user" || message?.role === "assistant")
    .filter((message) => {
      const content = typeof message.content === "string" ? message.content.trim() : "";
      return message.role !== "assistant" || message.status !== "pending" || content;
    })
    .map((message) => ({
      id: typeof message.id === "string" && message.id ? message.id : createConversationId(),
      role: message.role,
      content: typeof message.content === "string" ? message.content : "",
      status: message.status,
      error:
        message.status === "error"
          ? message.error_message || "챗봇 응답을 생성하지 못했습니다."
          : undefined,
      sources: Array.isArray(message.sources) ? message.sources : [],
      createdAt: typeof message.created_at === "string" ? message.created_at : new Date().toISOString(),
    }));
}

export function hasPendingAssistantResponse(response) {
  return Boolean(
    response?.messages?.some(
      (message) => message?.role === "assistant" && message?.status === "pending",
    ),
  );
}

export function shouldStopAssistantPollingAfterFailure(
  failureCount,
  maxFailures = ASSISTANT_POLL_MAX_FAILURES,
) {
  return Number(failureCount) >= maxFailures;
}

export function loadConversationState(scopeKey) {
  const fallback = {
    conversationId: createConversationId(),
    messages: [],
  };
  const storage = getConversationStorage();
  if (!storage) {
    return fallback;
  }
  try {
    const raw = storage.getItem(buildConversationStorageKey(scopeKey));
    if (!raw) {
      return fallback;
    }
    const parsed = JSON.parse(raw);
    return {
      conversationId:
        typeof parsed.conversationId === "string" && parsed.conversationId.trim()
          ? parsed.conversationId
          : fallback.conversationId,
      messages: sanitizeMessages(parsed.messages),
    };
  } catch {
    return fallback;
  }
}

export function saveConversationState(scopeKey, state) {
  const storage = getConversationStorage();
  if (!storage) {
    return;
  }
  const payload = {
    conversationId: state.conversationId || createConversationId(),
    messages: sanitizeMessages(state.messages),
    savedAt: new Date().toISOString(),
  };
  storage.setItem(buildConversationStorageKey(scopeKey), JSON.stringify(payload));
}

export function createConversationId() {
  if (globalThis.crypto?.randomUUID) {
    return globalThis.crypto.randomUUID();
  }
  return `local-${Date.now()}-${Math.random().toString(16).slice(2)}`;
}

function buildChatHistory(messages) {
  return sanitizeMessages(messages)
    .filter((message) => (
      !message.error
      && message.status !== "pending"
      && (message.role === "user" || message.role === "assistant")
    ))
    .slice(-MAX_HISTORY_MESSAGES)
    .map((message) => ({
      role: message.role,
      content: truncateHistoryContent(message.content),
    }));
}

function sanitizeMessages(messages) {
  if (!Array.isArray(messages)) {
    return [];
  }
  return messages
    .filter((message) => message && (message.role === "user" || message.role === "assistant"))
    .map((message) => ({
      id: typeof message.id === "string" && message.id ? message.id : createConversationId(),
      role: message.role,
      content: typeof message.content === "string" ? message.content : "",
      status: typeof message.status === "string" ? message.status : undefined,
      error: typeof message.error === "string" ? message.error : undefined,
      sources: Array.isArray(message.sources) ? message.sources : [],
      createdAt: typeof message.createdAt === "string" ? message.createdAt : new Date().toISOString(),
    }))
    .slice(-MAX_STORED_MESSAGES);
}

function truncateHistoryContent(content) {
  const compact = String(content ?? "").replace(/\s+/g, " ").trim();
  if (compact.length <= MAX_HISTORY_CONTENT_CHARS) {
    return compact;
  }
  return `${compact.slice(0, MAX_HISTORY_CONTENT_CHARS - 1).trim()}…`;
}

function buildConversationStorageKey(scopeKey) {
  return `${CONVERSATION_STORAGE_PREFIX}:${scopeKey}`;
}

function getConversationStorage() {
  try {
    return globalThis.sessionStorage ?? null;
  } catch {
    return null;
  }
}

export function formatRelevance(distance) {
  const value = Number(distance);
  if (!Number.isFinite(value)) {
    return null;
  }
  return `${(Math.max(0, 1 - value) * 100).toFixed(1)}%`;
}

export function sourceTypeLabel(sourceType) {
  if (sourceType === "report") {
    return "회의록";
  }
  if (sourceType === "note") {
    return "노트";
  }
  if (sourceType === "document") {
    return "문서";
  }
  if (sourceType === "transcript") {
    return "전사본";
  }
  if (sourceType === "event") {
    return "회의 이벤트";
  }
  if (sourceType === "session_summary") {
    return "노트 인사이트";
  }
  if (sourceType === "session") {
    return "회의";
  }
  return sourceType || "회의 자료";
}

export function sourceKindLabel(item) {
  const kind = item?.metadata_json?.source_kind;
  if (kind === "document") {
    return "문서";
  }
  if (kind === "note") {
    return "노트";
  }
  return null;
}

export function sectionRoleLabel(item) {
  const role = item?.metadata_json?.section_role;
  switch (role) {
    case "decision":
      return "결정";
    case "action_item":
      return "액션";
    case "risk":
      return "리스크";
    case "question":
      return "질문";
    case "summary":
      return "요약";
    case "discussion":
      return "논의";
    case "transcript":
      return "원문";
    default:
      return null;
  }
}

export function formatSourceTimeRange(item) {
  if (item?.start_ms == null && item?.end_ms == null) {
    return null;
  }
  return `${formatMs(item.start_ms)}-${formatMs(item.end_ms)}`;
}

export function buildSourceDetailConfig(item) {
  if (!item?.report_id) {
    return null;
  }
  return {
    type: "report",
    sessionId: item.session_id,
    reportId: item.report_id,
  };
}

function formatMs(value) {
  if (value == null) {
    return "?";
  }
  const totalSeconds = Math.max(0, Math.floor(Number(value) / 1000));
  const minutes = Math.floor(totalSeconds / 60);
  const seconds = totalSeconds % 60;
  return `${String(minutes).padStart(2, "0")}:${String(seconds).padStart(2, "0")}`;
}
