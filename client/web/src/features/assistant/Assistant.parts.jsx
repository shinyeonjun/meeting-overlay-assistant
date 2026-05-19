import React from "react";
import {
  AlertCircle,
  ArrowUp,
  FileText,
  Loader,
  MessageSquareText,
} from "lucide-react";

import {
  buildSourceDetailConfig,
  formatRelevance,
  sourceTypeLabel,
  SUGGESTED_QUESTIONS,
} from "./Assistant.helpers.js";

function SourceCard({ item, onOpenDetail, onOpenSession }) {
  const relevance = formatRelevance(item.distance);

  function handleOpenSource() {
    const detailConfig = buildSourceDetailConfig(item);
    if (detailConfig) {
      onOpenDetail(detailConfig);
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

export function AssistantMessage({ message, onOpenDetail, onOpenSession }) {
  if (message.role === "user") {
    return (
      <div className="assistant-message-row user">
        <div className="assistant-message-bubble user">{message.content}</div>
      </div>
    );
  }

  return (
    <div className="assistant-message-row assistant">
      <AssistantAvatar />
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

export function AssistantEmptyState({ initialSourceCount, onSuggestedQuestion }) {
  return (
    <section className="assistant-empty-state">
      <div className="assistant-empty-mark">
        <MessageSquareText size={28} />
      </div>
      <h2>회의 내용을 질문하세요</h2>
      <p>
        회의록, 노트 인사이트, 전사 근거를 찾아 답변합니다.
        {initialSourceCount > 0
          ? ` 지금 참고 가능한 근거 ${initialSourceCount}건이 있습니다.`
          : ""}
      </p>
      <div className="assistant-prompt-grid" aria-label="추천 질문">
        {SUGGESTED_QUESTIONS.map((item) => (
          <button
            key={item}
            className="assistant-prompt-card"
            onClick={() => onSuggestedQuestion(item)}
            type="button"
          >
            {item}
          </button>
        ))}
      </div>
    </section>
  );
}

export function AssistantMessageList({
  messages,
  onOpenDetail,
  onOpenSession,
  searching,
}) {
  return (
    <section className="assistant-message-list" aria-label="챗봇 대화">
      {messages.map((message) => (
        <AssistantMessage
          key={message.id}
          message={message}
          onOpenDetail={onOpenDetail}
          onOpenSession={onOpenSession}
        />
      ))}
      {searching ? <AssistantLoadingMessage /> : null}
    </section>
  );
}

function AssistantLoadingMessage() {
  return (
    <div className="assistant-message-row assistant">
      <AssistantAvatar />
      <div className="assistant-message-bubble assistant">
        <div className="assistant-loading">
          <Loader className="spinner" size={16} />
          관련 회의 근거를 찾고 답변을 정리하고 있습니다.
        </div>
      </div>
    </div>
  );
}

function AssistantAvatar() {
  return (
    <div className="assistant-avatar">
      <MessageSquareText size={15} />
    </div>
  );
}

export function AssistantComposer({
  onChange,
  onSubmit,
  onSubmitQuery,
  query,
  searching,
}) {
  return (
    <form className="assistant-composer" onSubmit={onSubmit}>
      <label className="assistant-composer-box">
        <textarea
          aria-label="챗봇 질문"
          onChange={onChange}
          onKeyDown={(event) => {
            if (event.key === "Enter" && !event.shiftKey) {
              event.preventDefault();
              onSubmitQuery();
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
  );
}
