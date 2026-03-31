import React, { useMemo, useState } from "react";
import {
  FileText,
  Filter,
  Mic,
  Search,
  Sparkles,
  Upload,
  Video,
} from "lucide-react";

import {
  formatDateTime,
  formatSourceLabel,
  getReportStatusLabel,
  getSessionStatusLabel,
  isLiveSession,
} from "../../app/workspace-model.js";

function normalizeSearchQuery(value) {
  return value.trim().toLowerCase();
}

function buildSearchIndex(fields) {
  return fields
    .filter(Boolean)
    .join(" ")
    .toLowerCase();
}

function getSourceIcon(source) {
  if (!source) {
    return Mic;
  }
  if (source.includes("video") || source.includes("zoom") || source.includes("system")) {
    return Video;
  }
  if (source.includes("upload")) {
    return Upload;
  }
  return Mic;
}

function matchesSessionQuery(session, query) {
  if (!query) {
    return true;
  }

  return buildSearchIndex([
    session.title,
    session.primary_input_source,
    session.status,
  ]).includes(query);
}

function matchesReportQuery(report, query) {
  if (!query) {
    return true;
  }

  return buildSearchIndex([
    report.report_type,
    report.session_id,
    report.generated_at,
  ]).includes(query);
}

function matchesRetrievalQuery(item, query) {
  if (!query) {
    return true;
  }

  return buildSearchIndex([
    item.document_title,
    item.chunk_text,
    item.session_id,
  ]).includes(query);
}

function filterItems(items, query, predicate) {
  if (!query) {
    return items;
  }
  return items.filter((item) => predicate(item, query));
}

function SectionLabel({ title, count, tone = "default" }) {
  return (
    <div className="inbox-section-label" data-tone={tone}>
      <strong>{title}</strong>
      <span>({count})</span>
    </div>
  );
}

function EmptyCard({ message }) {
  return <div className="inbox-empty-card">{message}</div>;
}

function StatusBadge({ tone, children }) {
  return <span className={`inbox-status-badge ${tone}`}>{children}</span>;
}

function SessionInboxCard({
  session,
  reportStatus,
  selected,
  tone,
  onSelect,
}) {
  const SourceIcon = getSourceIcon(session.primary_input_source);
  const badgeLabel = tone === "live"
    ? "LIVE"
    : reportStatus
      ? getReportStatusLabel(reportStatus.status)
      : getSessionStatusLabel(session.status);

  return (
    <button
      className={`inbox-session-card ${selected ? "selected" : ""}`}
      data-tone={tone}
      onClick={() => onSelect(session.id)}
      type="button"
    >
      <div className="inbox-session-head">
        <span className="inbox-session-title">{session.title || "제목 없는 세션"}</span>
        <StatusBadge tone={tone}>{badgeLabel}</StatusBadge>
      </div>
      <div className="inbox-session-meta">
        <span>{formatDateTime(session.started_at)}</span>
        <span className="inbox-meta-item">
          <SourceIcon size={12} />
          {formatSourceLabel(session.primary_input_source)}
        </span>
      </div>
    </button>
  );
}

function ReportInboxCard({ report, onOpen }) {
  return (
    <button
      className="inbox-session-card report"
      data-tone="report"
      onClick={() => onOpen(report)}
      type="button"
    >
      <div className="inbox-session-head">
        <span className="inbox-session-title">{report.report_type}</span>
        <StatusBadge tone="report">DOC</StatusBadge>
      </div>
      <div className="inbox-session-meta">
        <span>{formatDateTime(report.generated_at)}</span>
        <span className="inbox-meta-item">
          <FileText size={12} />
          생성된 문서
        </span>
      </div>
    </button>
  );
}

function RetrievalInboxCard({ item, onOpen }) {
  const relevance = (Math.max(0, 1 - Number(item.distance)) * 100).toFixed(0);

  return (
    <button
      className="inbox-session-card retrieval"
      data-tone="ready"
      onClick={() => onOpen(item)}
      type="button"
    >
      <div className="inbox-session-head">
        <span className="inbox-session-title">{item.document_title}</span>
        <StatusBadge tone="ready">{relevance}%</StatusBadge>
      </div>
      <p className="inbox-snippet">{item.chunk_text}</p>
    </button>
  );
}

function SessionSection({
  title,
  count,
  sessions,
  reportStatuses,
  selectedSessionId,
  onSelectSession,
  tone = "default",
  emptyMessage,
}) {
  return (
    <div className="inbox-section">
      <SectionLabel count={count} title={title} tone={tone} />
      <div className="inbox-card-list">
        {sessions.map((session) => (
          <SessionInboxCard
            key={session.id}
            onSelect={onSelectSession}
            reportStatus={reportStatuses[session.id]}
            selected={selectedSessionId === session.id}
            session={session}
            tone={tone}
          />
        ))}
        {sessions.length === 0 ? <EmptyCard message={emptyMessage} /> : null}
      </div>
    </div>
  );
}

export default function InboxPanel({
  activeMode,
  grouped,
  sessions,
  reports,
  reportStatuses,
  retrievalBrief,
  selectedSessionId,
  onSelectSession,
  onOpenReport,
  onOpenRetrieval,
}) {
  const [query, setQuery] = useState("");
  const normalizedQuery = normalizeSearchQuery(query);

  const running = useMemo(
    () => filterItems(grouped.running ?? [], normalizedQuery, matchesSessionQuery),
    [grouped.running, normalizedQuery],
  );
  const ready = useMemo(
    () => filterItems(grouped.ready ?? [], normalizedQuery, matchesSessionQuery),
    [grouped.ready, normalizedQuery],
  );
  const processing = useMemo(
    () => filterItems(grouped.processing ?? [], normalizedQuery, matchesSessionQuery),
    [grouped.processing, normalizedQuery],
  );
  const failed = useMemo(
    () => filterItems(grouped.failed ?? [], normalizedQuery, matchesSessionQuery),
    [grouped.failed, normalizedQuery],
  );
  const historySessions = useMemo(
    () => filterItems(sessions, normalizedQuery, matchesSessionQuery),
    [sessions, normalizedQuery],
  );
  const filteredReports = useMemo(
    () => filterItems(reports, normalizedQuery, matchesReportQuery),
    [reports, normalizedQuery],
  );
  const filteredRetrievalBrief = useMemo(
    () => filterItems(retrievalBrief, normalizedQuery, matchesRetrievalQuery),
    [retrievalBrief, normalizedQuery],
  );

  return (
    <section className="workspace-inbox">
      <div className="inbox-header">
        <div className="inbox-header-row">
          <h2>세션 인박스</h2>
          <button className="inbox-filter-button" type="button">
            <Filter size={16} />
          </button>
        </div>
        <label className="inbox-search-field">
          <Search size={14} />
          <input
            onChange={(event) => setQuery(event.target.value)}
            placeholder="세션 검색..."
            type="text"
            value={query}
          />
        </label>
      </div>

      <div className="inbox-scroll-area">
        {activeMode === "sessions" ? (
          <>
            <SessionSection
              count={running.length}
              emptyMessage="진행 중인 세션이 없습니다."
              onSelectSession={onSelectSession}
              reportStatuses={reportStatuses}
              selectedSessionId={selectedSessionId}
              sessions={running}
              title="진행 중"
              tone="live"
            />
            <SessionSection
              count={ready.length}
              emptyMessage="생성 가능한 세션이 없습니다."
              onSelectSession={onSelectSession}
              reportStatuses={reportStatuses}
              selectedSessionId={selectedSessionId}
              sessions={ready}
              title="리포트 생성 가능"
              tone="ready"
            />
            <SessionSection
              count={processing.length}
              emptyMessage="처리 중인 세션이 없습니다."
              onSelectSession={onSelectSession}
              reportStatuses={reportStatuses}
              selectedSessionId={selectedSessionId}
              sessions={processing}
              title="처리 중"
              tone="processing"
            />
            <SessionSection
              count={failed.length}
              emptyMessage="확인이 필요한 세션이 없습니다."
              onSelectSession={onSelectSession}
              reportStatuses={reportStatuses}
              selectedSessionId={selectedSessionId}
              sessions={failed}
              title="확인 필요"
              tone="failed"
            />
          </>
        ) : null}

        {activeMode === "history" ? (
          <SessionSection
            count={historySessions.length}
            emptyMessage="표시할 세션이 없습니다."
            onSelectSession={onSelectSession}
            reportStatuses={reportStatuses}
            selectedSessionId={selectedSessionId}
            sessions={historySessions}
            title="최근 세션"
            tone="default"
          />
        ) : null}

        {activeMode === "reports" ? (
          <>
            <SessionSection
              count={ready.length}
              emptyMessage="생성 대기 세션이 없습니다."
              onSelectSession={onSelectSession}
              reportStatuses={reportStatuses}
              selectedSessionId={selectedSessionId}
              sessions={ready}
              title="생성 대기"
              tone="ready"
            />
            <SessionSection
              count={processing.length}
              emptyMessage="처리 중인 세션이 없습니다."
              onSelectSession={onSelectSession}
              reportStatuses={reportStatuses}
              selectedSessionId={selectedSessionId}
              sessions={processing}
              title="처리 중"
              tone="processing"
            />
            <SessionSection
              count={failed.length}
              emptyMessage="확인이 필요한 세션이 없습니다."
              onSelectSession={onSelectSession}
              reportStatuses={reportStatuses}
              selectedSessionId={selectedSessionId}
              sessions={failed}
              title="확인 필요"
              tone="failed"
            />

            <div className="inbox-section">
              <SectionLabel count={filteredReports.length} title="최근 리포트" />
              <div className="inbox-card-list">
                {filteredReports.slice(0, 10).map((report) => (
                  <ReportInboxCard key={report.id} onOpen={onOpenReport} report={report} />
                ))}
                {filteredReports.length === 0 ? <EmptyCard message="최근 리포트가 없습니다." /> : null}
              </div>
            </div>
          </>
        ) : null}

        {activeMode === "assistant" ? (
          <>
            <div className="inbox-section">
              <SectionLabel count={3} title="빠른 질문" />
              <div className="prompt-chip-list">
                <span className="prompt-chip">
                  <Sparkles size={14} />
                  결정 사항 정리
                </span>
                <span className="prompt-chip">
                  <FileText size={14} />
                  액션 아이템 찾기
                </span>
                <span className="prompt-chip">
                  <Search size={14} />
                  관련 회의 찾기
                </span>
              </div>
            </div>

            <div className="inbox-section">
              <SectionLabel count={filteredRetrievalBrief.length} title="최근 검색 조각" />
              <div className="inbox-card-list">
                {filteredRetrievalBrief.map((item) => (
                  <RetrievalInboxCard key={item.chunk_id} item={item} onOpen={onOpenRetrieval} />
                ))}
                {filteredRetrievalBrief.length === 0 ? <EmptyCard message="최근 검색 결과가 없습니다." /> : null}
              </div>
            </div>
          </>
        ) : null}
      </div>
    </section>
  );
}
