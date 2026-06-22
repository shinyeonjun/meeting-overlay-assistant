import React, { useEffect, useMemo, useState } from "react";

import {
  buildConversationScopeKey,
} from "./Assistant.helpers.js";
import {
  getAssistantConversationSnapshot,
  loadAssistantConversations,
  removeAssistantConversation,
  refreshAssistantConversation,
  selectAssistantConversation,
  submitAssistantQuery,
  subscribeAssistantConversation,
  startNewAssistantConversation,
} from "./Assistant.conversation-store.js";
import {
  AssistantComposer,
  AssistantConversationSidebar,
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
  const [conversationItems, setConversationItems] = useState([]);
  const [conversationListLoading, setConversationListLoading] = useState(false);
  const [conversationListError, setConversationListError] = useState("");
  const [deletingConversationId, setDeletingConversationId] = useState("");
  const messages = conversationState.messages;
  const searching = conversationState.searching;

  async function refreshConversationList() {
    setConversationListLoading(true);
    setConversationListError("");
    try {
      const items = await loadAssistantConversations({ searchScope });
      setConversationItems(items);
    } catch (error) {
      setConversationListError(
        error instanceof Error ? error.message : "대화 목록을 불러오지 못했습니다.",
      );
    } finally {
      setConversationListLoading(false);
    }
  }

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

  useEffect(() => {
    void refreshConversationList();
  }, [
    conversationScopeKey,
    searchScope?.accountId,
    searchScope?.contactId,
    searchScope?.contextThreadId,
  ]);

  useEffect(() => {
    if (!searching) {
      void refreshConversationList();
    }
  }, [conversationState.conversationId, messages.length, searching]);

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

  function handleNewConversation() {
    startNewAssistantConversation(conversationScopeKey);
  }

  async function handleSelectConversation(conversationId) {
    if (!conversationId || conversationId === conversationState.conversationId) {
      return;
    }
    await selectAssistantConversation({
      scopeKey: conversationScopeKey,
      conversationId,
    });
  }

  async function handleDeleteConversation(conversationId) {
    if (!conversationId || deletingConversationId) {
      return;
    }
    const confirmed = globalThis.confirm?.("이 대화를 삭제할까요?");
    if (!confirmed) {
      return;
    }
    setDeletingConversationId(conversationId);
    try {
      await removeAssistantConversation({
        scopeKey: conversationScopeKey,
        conversationId,
      });
      await refreshConversationList();
    } finally {
      setDeletingConversationId("");
    }
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
    <div className="assistant-chat-shell animate-fade-in">
      <AssistantConversationSidebar
        activeConversationId={conversationState.conversationId}
        conversations={conversationItems}
        deletingConversationId={deletingConversationId}
        error={conversationListError}
        loading={conversationListLoading}
        onDeleteConversation={handleDeleteConversation}
        onNewConversation={handleNewConversation}
        onSelectConversation={handleSelectConversation}
      />
      <div className="assistant-chat-board">
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
    </div>
  );
}
