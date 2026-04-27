import React, { useEffect, useMemo, useState } from "react";
import {
  AlertCircle,
  ArrowUp,
  FileText,
  Loader,
  MessageSquareText,
} from "lucide-react";

import { searchRetrieval } from "../../services/retrieval-api.js";

const SUGGESTED_QUESTIONS = [
  "지난 회의에서 결정된 다음 할 일은?",
  "아직 남은 질문이나 리스크는?",
  "최근 회의에서 중요한 결정만 정리해줘",
  "회의록 공유 전에 확인할 내용은?",
];

function buildSearchRequest(query, searchScope) {
  return {
    query,
    limit: 10,
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
        <span>{item.source_type || "회의 자료"}</span>
        <span>{item.session_id ? "관련 회의 열기" : "관련 근거"}</span>
      </div>
    </button>
  );
}

export default function Assistant({
  initialBrief,
  searchScope,
  onOpenSession,
  onOpenDetail,
}) {
  const [query, setQuery] = useState(initialBrief?.query ?? "");
  const [submittedQuery, setSubmittedQuery] = useState(initialBrief?.query ?? "");
  const [results, setResults] = useState(initialBrief?.items ?? []);
  const [searching, setSearching] = useState(false);
  const [error, setError] = useState(null);

  const resultCount = useMemo(() => results?.length ?? 0, [results]);
  const hasConversation = Boolean(submittedQuery || searching || error);

  useEffect(() => {
    setQuery(initialBrief?.query ?? "");
    setSubmittedQuery(initialBrief?.query ?? "");
    setResults(initialBrief?.items ?? []);
    setError(null);
  }, [initialBrief]);

  async function runSearch(nextQuery) {
    const normalized = nextQuery.trim();
    if (!normalized) {
      setResults([]);
      setSubmittedQuery("");
      return;
    }

    try {
      setSubmittedQuery(normalized);
      setSearching(true);
      setError(null);
      const response = await searchRetrieval(buildSearchRequest(normalized, searchScope));
      setResults(response.items ?? []);
    } catch (nextError) {
      setResults([]);
      setError(nextError instanceof Error ? nextError.message : "질문 요청에 실패했습니다.");
    } finally {
      setSearching(false);
    }
  }

  function handleSearch(event) {
    event.preventDefault();
    void runSearch(query);
  }

  function handleSuggestedQuestion(nextQuery) {
    setQuery(nextQuery);
    void runSearch(nextQuery);
  }

  return (
    <div className="assistant-chat-board animate-fade-in">
      <div className="assistant-chat-scroll">
        {!hasConversation ? (
          <section className="assistant-empty-state">
            <div className="assistant-empty-mark">
              <MessageSquareText size={28} />
            </div>
            <h2>무엇을 확인할까요?</h2>
            <p>회의 전사, 노트, 회의록에서 근거를 찾아 답변합니다.</p>
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
            {submittedQuery ? (
              <div className="assistant-message-row user">
                <div className="assistant-message-bubble user">{submittedQuery}</div>
              </div>
            ) : null}

            <div className="assistant-message-row assistant">
              <div className="assistant-avatar">
                <MessageSquareText size={15} />
              </div>
              <div className="assistant-message-bubble assistant">
                {searching ? (
                  <div className="assistant-loading">
                    <Loader className="spinner" size={16} />
                    관련 근거를 찾고 있습니다.
                  </div>
                ) : error ? (
                  <div className="assistant-error">
                    <AlertCircle size={16} />
                    {error}
                  </div>
                ) : (
                  <>
                    <p className="assistant-answer-copy">
                      질문과 맞는 회의 근거 {resultCount}건을 찾았습니다. 아래 항목에서
                      원문을 열어 확인할 수 있습니다.
                    </p>
                    {resultCount > 0 ? (
                      <div className="assistant-source-list">
                        {results.map((item) => (
                          <SourceCard
                            key={item.chunk_id}
                            item={item}
                            onOpenDetail={onOpenDetail}
                            onOpenSession={onOpenSession}
                          />
                        ))}
                      </div>
                    ) : (
                      <div className="assistant-no-result">
                        일치하는 근거를 찾지 못했습니다. 회의 제목이나 날짜를 포함해 다시 질문해보세요.
                      </div>
                    )}
                  </>
                )}
              </div>
            </div>
          </section>
        )}
      </div>

      <form className="assistant-composer" onSubmit={handleSearch}>
        <label className="assistant-composer-box">
          <textarea
            aria-label="챗봇 질문"
            onChange={(event) => setQuery(event.target.value)}
            onKeyDown={(event) => {
              if (event.key === "Enter" && !event.shiftKey) {
                event.preventDefault();
                if (!searching) {
                  void runSearch(query);
                }
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
        <p>CAPS는 회의 자료에서 근거를 찾아 보여줍니다. 공유 전에는 원문을 확인하세요.</p>
      </form>
    </div>
  );
}
