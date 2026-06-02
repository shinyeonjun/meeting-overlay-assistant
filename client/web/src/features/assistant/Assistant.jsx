import React, { useEffect, useMemo, useState } from "react";

import {
  buildConversationScopeKey,
} from "./Assistant.helpers.js";
import {
  getAssistantConversationSnapshot,
  refreshAssistantConversation,
  submitAssistantQuery,
  subscribeAssistantConversation,
} from "./Assistant.conversation-store.js";
import {
  AssistantComposer,
  AssistantEmptyState,
  AssistantMessageList,
} from "./Assistant.parts.jsx";

export default function Assistant({
  initialBrief,
  searchScope,
  onOpenSession,
  onOpenDetail,
}) {
  const conversationScopeKey = useMemo(
    () => buildConversationScopeKey(searchScope),
    [
      searchScope?.accountId,
      searchScope?.contactId,
      searchScope?.contextThreadId,
      searchScope?.userId,
    ],
  );
  const [query, setQuery] = useState(initialBrief?.query ?? "");
  const [conversationState, setConversationState] = useState(() =>
    getAssistantConversationSnapshot(conversationScopeKey),
  );
  const messages = conversationState.messages;
  const searching = conversationState.searching;

  useEffect(() => {
    const snapshot = getAssistantConversationSnapshot(conversationScopeKey);
    if (snapshot.messages.length > 0) {
      void refreshAssistantConversation({
        scopeKey: conversationScopeKey,
        conversationId: snapshot.conversationId,
      });
    }
    return subscribeAssistantConversation(
      conversationScopeKey,
      setConversationState,
    );
  }, [conversationScopeKey]);

  const hasConversation = messages.length > 0 || searching;
  const initialSourceCount = useMemo(
    () => initialBrief?.items?.length ?? 0,
    [initialBrief],
  );

  async function runChat(nextQuery) {
    const normalized = nextQuery.trim();
    if (!normalized || searching) {
      return;
    }

    setQuery("");
    submitAssistantQuery({
      scopeKey: conversationScopeKey,
      searchScope,
      query: normalized,
    });
  }

  function handleSubmit(event) {
    event.preventDefault();
    void runChat(query);
  }

  function handleSuggestedQuestion(nextQuery) {
    setQuery(nextQuery);
    void runChat(nextQuery);
  }

  return (
    <div className="assistant-chat-board animate-fade-in">
      <div className="assistant-chat-scroll">
        {!hasConversation ? (
          <AssistantEmptyState
            initialSourceCount={initialSourceCount}
            onSuggestedQuestion={handleSuggestedQuestion}
          />
        ) : (
          <AssistantMessageList
            messages={messages}
            onOpenDetail={onOpenDetail}
            onOpenSession={onOpenSession}
            searching={searching}
          />
        )}
      </div>

      <AssistantComposer
        onChange={(event) => setQuery(event.target.value)}
        onSubmit={handleSubmit}
        onSubmitQuery={() => void runChat(query)}
        query={query}
        searching={searching}
      />
    </div>
  );
}
