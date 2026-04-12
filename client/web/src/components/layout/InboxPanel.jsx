/** 웹 공용 UI에서 InboxPanel 컴포넌트를 제공한다. */
import React, { useEffect, useMemo, useRef, useState } from "react";
import { MoreHorizontal, Pencil, RefreshCcw, Trash2 } from "lucide-react";

import { formatDateTime, resolveWorkflowStatus } from "../../app/workspace-model.js";

function buildSearchIndex(session) {
  return [session.title, session.status, session.primary_input_source]
    .filter(Boolean)
    .join(" ")
    .toLowerCase();
}

function filterSessions(sessions, searchQuery) {
  const normalized = searchQuery.trim().toLowerCase();
  if (!normalized) {
    return sessions;
  }

  return sessions.filter((session) => buildSearchIndex(session).includes(normalized));
}

function SessionCard({
  isActive = false,
  onDeleteSession,
  onRenameSession,
  onReprocessSession,
  onSelect,
  reportStatus,
  session,
}) {
  const workflow = resolveWorkflowStatus(session, reportStatus);
  const [menuOpen, setMenuOpen] = useState(false);
  const menuRef = useRef(null);
  const reprocessLabel = session.recovery_required ? "노트 만들기" : "노트 재생성";

  useEffect(() => {
    if (!menuOpen) {
      return undefined;
    }

    function handlePointerDown(event) {
      if (!menuRef.current?.contains(event.target)) {
        setMenuOpen(false);
      }
    }

    document.addEventListener("mousedown", handlePointerDown);
    return () => {
      document.removeEventListener("mousedown", handlePointerDown);
    };
  }, [menuOpen]);

  function handleMenuAction(action) {
    setMenuOpen(false);
    action(session);
  }

  return (
    <div className={`caps-session-card ${isActive ? "active" : ""}`}>
      <button
        className="caps-session-card-main"
        onClick={() => onSelect(session.id)}
        type="button"
      >
        <p className="caps-session-title">{session.title || "제목 없는 회의"}</p>
        <p className="caps-session-meta">
          {formatDateTime(session.started_at)} · {workflow.label}
        </p>
      </button>

      <div ref={menuRef} className="caps-session-card-menu">
        <button
          aria-label="세션 더보기"
          className="caps-session-more-button"
          onClick={() => setMenuOpen((current) => !current)}
          type="button"
        >
          <MoreHorizontal size={15} />
        </button>

        {menuOpen ? (
          <div className="caps-session-menu-dropdown">
            <button
              className="caps-session-menu-item"
              onClick={() => handleMenuAction(onRenameSession)}
              type="button"
            >
              <Pencil size={14} />
              이름 바꾸기
            </button>
            <button
              className="caps-session-menu-item"
              onClick={() => handleMenuAction(onReprocessSession)}
              type="button"
            >
              <RefreshCcw size={14} />
              {reprocessLabel}
            </button>
            <button
              className="caps-session-menu-item danger"
              onClick={() => handleMenuAction(onDeleteSession)}
              type="button"
            >
              <Trash2 size={14} />
              삭제
            </button>
          </div>
        ) : null}
      </div>
    </div>
  );
}

function SectionHeader({ active = false, title }) {
  return (
    <div className={`caps-session-group-title ${active ? "active" : ""}`}>
      {active ? <span className="caps-live-dot" /> : null}
      <span>{title}</span>
    </div>
  );
}

export default function InboxPanel({
  grouped,
  onDeleteSession,
  onRenameSession,
  onReprocessSession,
  onSelectSession,
  reportStatuses,
  searchQuery,
  selectedSessionId,
  sessions,
}) {
  const filteredSessions = useMemo(
    () => filterSessions(sessions, searchQuery),
    [searchQuery, sessions],
  );

  const runningIds = new Set((grouped.running ?? []).map((session) => session.id));
  const filteredRunning = filteredSessions.filter((session) => runningIds.has(session.id));
  const completedSessions = filteredSessions
    .filter((session) => !runningIds.has(session.id))
    .slice(0, 12);

  return (
    <section className="caps-session-list-panel">
      <div className="caps-session-list-header">
        <h2>최근 세션</h2>
      </div>

      <div className="caps-session-list-scroll">
        <div className="caps-session-group">
          <SectionHeader active title="진행 중" />
          {filteredRunning.length > 0 ? (
            filteredRunning.map((session) => (
              <SessionCard
                key={session.id}
                isActive={selectedSessionId === session.id}
                onDeleteSession={onDeleteSession}
                onRenameSession={onRenameSession}
                onReprocessSession={onReprocessSession}
                onSelect={onSelectSession}
                reportStatus={reportStatuses[session.id]}
                session={session}
              />
            ))
          ) : (
            <div className="caps-session-empty">진행 중인 회의가 없습니다.</div>
          )}
        </div>

        <div className="caps-session-group">
          <SectionHeader title="나머지 세션" />
          {completedSessions.length > 0 ? (
            completedSessions.map((session) => (
              <SessionCard
                key={session.id}
                isActive={selectedSessionId === session.id}
                onDeleteSession={onDeleteSession}
                onRenameSession={onRenameSession}
                onReprocessSession={onReprocessSession}
                onSelect={onSelectSession}
                reportStatus={reportStatuses[session.id]}
                session={session}
              />
            ))
          ) : (
            <div className="caps-session-empty">표시할 세션이 없습니다.</div>
          )}
        </div>
      </div>
    </section>
  );
}
