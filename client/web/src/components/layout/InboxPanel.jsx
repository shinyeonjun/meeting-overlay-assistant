import React, { useEffect, useMemo, useRef, useState } from "react";
import { MoreHorizontal, Pencil, RefreshCcw, Trash2 } from "lucide-react";

import {
  formatDateTime,
  getMeetingStatusLabel,
  resolveMeetingWorkflowStatus,
} from "../../app/workspace-model.js";

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

function buildGroupedLists({ filteredSessions, reportStatuses }) {
  const filteredRunning = [];
  const filteredActionNeeded = [];
  const filteredRecent = [];

  filteredSessions.forEach((session) => {
    const workflow = resolveMeetingWorkflowStatus(session, reportStatuses?.[session.id]);
    if (workflow.category === "running") {
      filteredRunning.push(session);
      return;
    }
    if (workflow.category === "processing" || workflow.category === "failed" || workflow.category === "recovery_required") {
      filteredActionNeeded.push(session);
      return;
    }
    filteredRecent.push(session);
  });

  filteredRecent.splice(12);

  return {
    filteredActionNeeded,
    filteredRecent,
    filteredRunning,
  };
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
  const workflow = resolveMeetingWorkflowStatus(session, reportStatus);
  const [menuOpen, setMenuOpen] = useState(false);
  const menuRef = useRef(null);
  const reprocessLabel = session.recovery_required ? "노트 만들기" : "다시 정리하기";

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
        <div className="caps-session-meta-row">
          <p className="caps-session-meta">{formatDateTime(session.started_at)}</p>
          <span className={`caps-session-status-pill ${workflow.tone}`}>
            {getMeetingStatusLabel(reportStatus, session)}
          </span>
        </div>
      </button>

      <div ref={menuRef} className="caps-session-card-menu">
        <button
          aria-label="회의 옵션 보기"
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

function SessionSection({
  emptyCopy,
  isLive = false,
  items,
  onDeleteSession,
  onRenameSession,
  onReprocessSession,
  onSelectSession,
  reportStatuses,
  selectedSessionId,
  title,
}) {
  return (
    <div className="caps-session-group">
      <SectionHeader active={isLive} title={title} />
      {items.length > 0 ? (
        items.map((session) => (
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
        <div className="caps-session-empty">{emptyCopy}</div>
      )}
    </div>
  );
}

export default function InboxPanel({
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

  const { filteredActionNeeded, filteredRecent, filteredRunning } = useMemo(
    () => buildGroupedLists({ filteredSessions, reportStatuses }),
    [filteredSessions, reportStatuses],
  );

  return (
    <section className="caps-session-list-panel">
      <div className="caps-session-list-header">
        <h2>회의 목록</h2>
      </div>

      <div className="caps-session-list-scroll">
        <SessionSection
          emptyCopy="진행 중인 회의가 없습니다."
          isLive
          items={filteredRunning}
          onDeleteSession={onDeleteSession}
          onRenameSession={onRenameSession}
          onReprocessSession={onReprocessSession}
          onSelectSession={onSelectSession}
          reportStatuses={reportStatuses}
          selectedSessionId={selectedSessionId}
          title="진행 중"
        />

        <SessionSection
          emptyCopy="확인하거나 다시 정리할 회의가 없습니다."
          items={filteredActionNeeded}
          onDeleteSession={onDeleteSession}
          onRenameSession={onRenameSession}
          onReprocessSession={onReprocessSession}
          onSelectSession={onSelectSession}
          reportStatuses={reportStatuses}
          selectedSessionId={selectedSessionId}
          title="작업 필요"
        />

        <SessionSection
          emptyCopy="표시할 회의가 없습니다."
          items={filteredRecent}
          onDeleteSession={onDeleteSession}
          onRenameSession={onRenameSession}
          onReprocessSession={onReprocessSession}
          onSelectSession={onSelectSession}
          reportStatuses={reportStatuses}
          selectedSessionId={selectedSessionId}
          title="최근 완료"
        />
      </div>
    </section>
  );
}
