import React, { useMemo, useState } from "react";
import {
  AlertCircle,
  ArrowUp,
  FileText,
  Loader,
  MessageSquareText,
} from "lucide-react";

import { chatAssistant } from "../../services/assistant-api.js";

const SUGGESTED_QUESTIONS = [
  "지난 회의에서 결정된 다음 할 일은?",
  "아직 남은 질문이나 리스크는?",
  "최근 회의에서 중요한 결정만 정리해줘",
  "공유 전에 확인해야 할 내용은?",
];

function buildChatRequest(query, searchScope) {
  return {
    query,
    limit: 8,
    accountId: searchScope?.accountId,
    contactId: searchScope?.contactId,
    contextThreadId: searchScope?.contextThreadId,
  };
}

function formatRelevance(distance) {
  const value = Number(distance);
  if (!Number.isFinite(value)) {
    return null;
  }
  return `${(Math.max(0, 1 - value) * 100).toFixed(1)}%`;
}

function sourceTypeLabel(sourceType) {
  if (sourceType === "report") {
    return "회의록";
  }
  if (sourceType === "session_summary") {
    return "노트 인사이트";
  }
  return sourceType || "회의 자료";
}

function SourceCard({ item, onOpenDetail, onOpenSession }) {
  const relevance = formatRelevance(item.distance);

  function handleOpenSource() {
    if (item.report_id) {
      onOpenDetail({
        type: "report",
        sessionId: item.session_id,
        reportId: item.report_id,
      });
      return;
    }
    if (item.session_id) {
      onOpenSession(item.session_id);
    }
  }

  return (
    <button className="assistant-source-card" onClick={handleOpenSource} type="button">
      <div className="assistant-source-card-head">
        <div className="assistant-source-title">
          <FileText size={15} />
          <strong>{item.document_title || "회의 근거"}</strong>
        </div>
        {relevance ? <span>{relevance}</span> : null}
      </div>
      <p>{item.chunk_text}</p>
      <div className="assistant-source-meta">
        <span>{sourceTypeLabel(item.source_type)}</span>
        <span>{item.chunk_heading || "본문"}</span>
      </div>
    </button>
  );
}

function AssistantMessage({ message, onOpenDetail, onOpenSession }) {
  if (message.role === "user") {
    return (
      <div className="assistant-message-row user">
        <div className="assistant-message-bubble user">{message.content}</div>
      </div>
    );
  }

  return (
    <div className="assistant-message-row assistant">
      <div className="assistant-avatar">
        <MessageSquareText size={15} />
      </div>
      <div className="assistant-message-bubble assistant">
        {message.error ? (
          <div className="assistant-error">
            <AlertCircle size={16} />
            {message.error}
          </div>
        ) : (
          <>
            <p className="assistant-answer-copy">{message.content}</p>
            {message.sources?.length ? (
              <div className="assistant-source-list">
                {message.sources.map((item) => (
                  <SourceCard
                    key={item.chunk_id}
                    item={item}
                    onOpenDetail={onOpenDetail}
                    onOpenSession={onOpenSession}
                  />
                ))}
              </div>
            ) : null}
          </>
        )}
      </div>
    </div>
  );
}

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

    const userMessage = {
      id: `user-${Date.now()}`,
      role: "user",
      content: normalized,
    };
    setMessages((current) => [...current, userMessage]);
    setQuery("");
    setSearching(true);

    try {
      const response = await chatAssistant(buildChatRequest(normalized, searchScope));
      setMessages((current) => [
        ...current,
        {
          id: `assistant-${Date.now()}`,
          role: "assistant",
          content: response.answer,
          sources: response.sources ?? [],
        },
      ]);
    } catch (nextError) {
      setMessages((current) => [
        ...current,
        {
          id: `assistant-error-${Date.now()}`,
          role: "assistant",
          content: "",
          error:
            nextError instanceof Error
              ? nextError.message
              : "챗봇 답변을 생성하지 못했습니다.",
        },
      ]);
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
          <section className="assistant-empty-state">
            <div className="assistant-empty-mark">
              <MessageSquareText size={28} />
            </div>
            <h2>회의 내용을 질문하세요</h2>
            <p>
              회의록, 노트 인사이트, 전사 근거를 찾아 답변합니다.
              {initialSourceCount > 0 ? ` 지금 참고 가능한 근거 ${initialSourceCount}건이 있습니다.` : ""}
            </p>
            <div className="assistant-prompt-grid" aria-label="추천 질문">
              {SUGGESTED_QUESTIONS.map((item) => (
                <button
                  key={item}
                  className="assistant-prompt-card"
                  onClick={() => handleSuggestedQuestion(item)}
                  type="button"
                >
                  {item}
                </button>
              ))}
            </div>
          </section>
        ) : (
          <section className="assistant-message-list" aria-label="챗봇 대화">
            {messages.map((message) => (
              <AssistantMessage
                key={message.id}
                message={message}
                onOpenDetail={onOpenDetail}
                onOpenSession={onOpenSession}
              />
            ))}
            {searching ? (
              <div className="assistant-message-row assistant">
                <div className="assistant-avatar">
                  <MessageSquareText size={15} />
                </div>
                <div className="assistant-message-bubble assistant">
                  <div className="assistant-loading">
                    <Loader className="spinner" size={16} />
                    관련 회의 근거를 찾고 답변을 정리하고 있습니다.
                  </div>
                </div>
              </div>
            ) : null}
          </section>
        )}
      </div>

      <form className="assistant-composer" onSubmit={handleSubmit}>
        <label className="assistant-composer-box">
          <textarea
            aria-label="챗봇 질문"
            onChange={(event) => setQuery(event.target.value)}
            onKeyDown={(event) => {
              if (event.key === "Enter" && !event.shiftKey) {
                event.preventDefault();
                void runChat(query);
              }
            }}
            placeholder="회의 내용 질문하기"
            rows={1}
            value={query}
          />
          <button
            className="assistant-send-button"
            disabled={searching || !query.trim()}
            type="submit"
          >
            {searching ? <Loader className="spinner" size={16} /> : <ArrowUp size={17} />}
          </button>
        </label>
        <p>CAPS는 저장된 회의 자료에서 근거를 찾아 답변합니다. 공유 전에는 원문을 확인하세요.</p>
      </form>
    </div>
  );
}
