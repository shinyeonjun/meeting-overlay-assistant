import React, { useEffect, useMemo, useState } from "react";
import { AlertCircle, FileText, Loader, MessageSquareText, Search } from "lucide-react";

import { searchRetrieval } from "../../services/retrieval-api.js";

function buildSearchRequest(query, searchScope) {
  return {
    query,
    limit: 10,
    accountId: searchScope?.accountId,
    contactId: searchScope?.contactId,
    contextThreadId: searchScope?.contextThreadId,
  };
}

export default function Assistant({
  initialBrief,
  searchScope,
  onOpenSession,
  onOpenDetail,
}) {
  const [query, setQuery] = useState(initialBrief?.query ?? "");
  const [results, setResults] = useState(initialBrief?.items ?? []);
  const [searching, setSearching] = useState(false);
  const [error, setError] = useState(null);

  const resultCount = useMemo(() => results?.length ?? 0, [results]);

  useEffect(() => {
    setQuery(initialBrief?.query ?? "");
    setResults(initialBrief?.items ?? []);
    setError(null);
  }, [initialBrief]);

  async function handleSearch(event) {
    event.preventDefault();
    const normalized = query.trim();
    if (!normalized) {
      setResults([]);
      return;
    }

    try {
      setSearching(true);
      setError(null);
      const response = await searchRetrieval(buildSearchRequest(normalized, searchScope));
      setResults(response.items ?? []);
    } catch (nextError) {
      setError(nextError instanceof Error ? nextError.message : "검색 요청에 실패했습니다.");
    } finally {
      setSearching(false);
    }
  }

  return (
    <div className="assistant-board animate-fade-in">
      <section className="section-heading-row">
        <div>
          <span className="section-kicker">RETRIEVAL WORKSPACE</span>
          <h2>세션과 회의록을 기반으로 후속 질문에 답합니다.</h2>
          <p>
            assistant는 제품 중심 쇼케이스가 아니라, 이미 생성된 세션/회의록을 다시 찾고
            검증하는 후처리 도구에 가깝습니다.
          </p>
        </div>
      </section>

      <section className="workspace-panel">
        <div className="panel-title-row">
          <div className="panel-title-left">
            <MessageSquareText size={16} />
            <h3>검색 질의</h3>
          </div>
          <span>{resultCount}건</span>
        </div>

        <form className="assistant-query-form" onSubmit={handleSearch}>
          <label className="assistant-query-box">
            <Search size={18} />
            <input
              type="text"
              value={query}
              onChange={(event) => setQuery(event.target.value)}
              placeholder="예: 지난 회의에서 결정된 액션 아이템 정리해줘"
            />
          </label>
          <button className="primary-button" disabled={searching} type="submit">
            {searching ? (
              <>
                <Loader size={16} className="spinner" />
                검색 중
              </>
            ) : (
              "검색"
            )}
          </button>
        </form>

        {error ? (
          <div className="inline-banner error">
            <AlertCircle size={16} />
            {error}
          </div>
        ) : null}
      </section>

      <section className="assistant-results-grid">
        {results.length > 0 ? (
          results.map((item) => (
            <button
              key={item.chunk_id}
              className="assistant-result-card"
              onClick={() => {
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
              }}
              type="button"
            >
              <div className="assistant-result-head">
                <div className="assistant-result-title">
                  <FileText size={16} />
                  <strong>{item.document_title}</strong>
                </div>
                <span className="status-pill ready">
                  관련도 {(Math.max(0, 1 - Number(item.distance)) * 100).toFixed(1)}%
                </span>
              </div>
              <p>{item.chunk_text}</p>
              <div className="assistant-result-foot">
                <span>{item.source_type}</span>
                <span>{item.session_id ? "세션 연결 가능" : "회의록 중심 결과"}</span>
              </div>
            </button>
          ))
        ) : (
          <div className="workspace-panel panel-empty-large">
            아직 검색 결과가 없습니다. 위 질의창에서 세션이나 회의록을 다시 찾아보세요.
          </div>
        )}
      </section>
    </div>
  );
}
