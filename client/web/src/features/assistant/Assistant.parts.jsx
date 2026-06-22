import React from "react";
import {
  AlertCircle,
  ArrowUp,
  FileText,
  Loader,
  MessageSquare,
  MessageSquareText,
  Plus,
  Trash2,
} from "lucide-react";

import {
  buildSourceDetailConfig,
  formatSourceTimeRange,
  sectionRoleLabel,
  sourceKindLabel,
  sourceTypeLabel,
  SUGGESTED_QUESTIONS,
} from "./Assistant.helpers.js";

const MAX_VISIBLE_SOURCES = 4;
const SOURCE_SNIPPET_MAX_CHARS = 140;

function formatConversationTime(value) {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return "";
  }
  return new Intl.DateTimeFormat("ko-KR", {
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
  }).format(date);
}

export function AssistantConversationSidebar({
  activeConversationId,
  conversations,
  deletingConversationId,
  error,
  loading,
  onDeleteConversation,
  onNewConversation,
  onSelectConversation,
}) {
  return (
    <aside className="assistant-conversation-panel" aria-label="챗봇 대화 세션">
      <div className="assistant-conversation-panel-head">
        <h2>대화</h2>
        <button
          className="assistant-new-chat-button"
          onClick={onNewConversation}
          title="새 대화"
          type="button"
        >
          <Plus size={16} />
        </button>
      </div>
      <button
        className="assistant-new-chat-row"
        onClick={onNewConversation}
        type="button"
      >
        <MessageSquare size={16} />
        <span>새 대화</span>
      </button>
      <div className="assistant-conversation-list" role="list">
        {loading && conversations.length === 0 ? (
          <div className="assistant-conversation-muted">대화 목록을 불러오는 중입니다.</div>
        ) : null}
        {error ? (
          <div className="assistant-conversation-muted danger">{error}</div>
        ) : null}
        {!loading && conversations.length === 0 ? (
          <div className="assistant-conversation-muted">저장된 대화가 없습니다.</div>
        ) : null}
        {conversations.map((conversation) => (
          <ConversationListItem
            active={conversation.conversation_id === activeConversationId}
            conversation={conversation}
            deleting={conversation.conversation_id === deletingConversationId}
            key={conversation.conversation_id}
            onDeleteConversation={onDeleteConversation}
            onSelectConversation={onSelectConversation}
          />
        ))}
      </div>
    </aside>
  );
}

function ConversationListItem({
  active,
  conversation,
  deleting,
  onDeleteConversation,
  onSelectConversation,
}) {
  return (
    <div className={`assistant-conversation-item${active ? " active" : ""}`} role="listitem">
      <button
        className="assistant-conversation-select"
        onClick={() => onSelectConversation(conversation.conversation_id)}
        type="button"
      >
        <span>{conversation.title || "새 대화"}</span>
        <time>{formatConversationTime(conversation.updated_at)}</time>
      </button>
      <button
        className="assistant-conversation-delete"
        disabled={deleting}
        onClick={() => onDeleteConversation(conversation.conversation_id)}
        title="대화 삭제"
        type="button"
      >
        {deleting ? <Loader className="spinner" size={14} /> : <Trash2 size={14} />}
      </button>
    </div>
  );
}

function AssistantSources({ sources, onOpenDetail, onOpenSession }) {
  const visibleSources = selectVisibleSources(sources);
  if (!visibleSources.length) {
    return null;
  }

  return (
    <details className="assistant-source-drawer">
      <summary>
        <FileText size={14} />
        <span>근거 {visibleSources.length}개</span>
      </summary>
      <div className="assistant-source-list">
        {visibleSources.map((item, index) => (
          <SourceCard
            index={index + 1}
            item={item}
            key={item.chunk_id}
            onOpenDetail={onOpenDetail}
            onOpenSession={onOpenSession}
          />
        ))}
      </div>
    </details>
  );
}

function SourceCard({ index, item, onOpenDetail, onOpenSession }) {
  const kindLabel = sourceKindLabel(item);
  const roleLabel = sectionRoleLabel(item);
  const timeRange = formatSourceTimeRange(item);

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
        <span className="assistant-source-index">S{index}</span>
        <strong>{item.document_title || "회의 근거"}</strong>
      </div>
      <p>{formatSourceSnippet(item.chunk_text)}</p>
      <div className="assistant-source-meta">
        <span>{sourceTypeLabel(item.source_type)}</span>
        {kindLabel ? <span>{kindLabel}</span> : null}
        {roleLabel ? <span>{roleLabel}</span> : null}
        {timeRange ? <span>{timeRange}</span> : null}
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
            <AssistantSources
              onOpenDetail={onOpenDetail}
              onOpenSession={onOpenSession}
              sources={message.sources}
            />
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
        회의록과 노트 원문에서 근거를 찾아 답변합니다.
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
          관련 근거를 찾고 답변을 정리하고 있습니다.
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
      <p>CAPS는 저장된 회의 자료에서 근거를 찾아 답변합니다.</p>
    </form>
  );
}

function selectVisibleSources(sources = []) {
  if (!Array.isArray(sources)) {
    return [];
  }
  return sources
    .filter((item) => item?.chunk_id && item?.document_title)
    .slice(0, MAX_VISIBLE_SOURCES);
}

function formatSourceSnippet(text) {
  const normalized = String(text ?? "").replace(/\s+/g, " ").trim();
  if (!normalized) {
    return "근거 본문 없음";
  }
  if (normalized.length <= SOURCE_SNIPPET_MAX_CHARS) {
    return normalized;
  }
  return `${normalized.slice(0, SOURCE_SNIPPET_MAX_CHARS - 1).trim()}…`;
}
