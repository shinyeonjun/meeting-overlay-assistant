import React, { useMemo, useState } from "react";

import { chatAssistant } from "../../services/assistant-api.js";
import { buildChatRequest } from "./Assistant.helpers.js";
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
  const [query, setQuery] = useState(initialBrief?.query ?? "");
  const [messages, setMessages] = useState([]);
  const [searching, setSearching] = useState(false);

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

    setMessages((current) => [...current, buildUserMessage(normalized)]);
    setQuery("");
    setSearching(true);

    try {
      const response = await chatAssistant(buildChatRequest(normalized, searchScope));
      setMessages((current) => [...current, buildAssistantMessage(response)]);
    } catch (nextError) {
      setMessages((current) => [...current, buildAssistantErrorMessage(nextError)]);
    } finally {
      setSearching(false);
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

function buildUserMessage(content) {
  return {
    id: `user-${Date.now()}`,
    role: "user",
    content,
  };
}

function buildAssistantMessage(response) {
  return {
    id: `assistant-${Date.now()}`,
    role: "assistant",
    content: response.answer,
    sources: response.sources ?? [],
  };
}

function buildAssistantErrorMessage(error) {
  return {
    id: `assistant-error-${Date.now()}`,
    role: "assistant",
    content: "",
    error:
      error instanceof Error
        ? error.message
        : "챗봇 응답을 생성하지 못했습니다.",
  };
}
