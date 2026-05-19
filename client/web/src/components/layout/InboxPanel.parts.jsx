import React, { useEffect, useRef, useState } from "react";
import { MoreHorizontal, Pencil, RefreshCcw, Trash2 } from "lucide-react";

import {
  formatDateTime,
  getMeetingStatusLabel,
} from "../../app/workspace-model.js";
import { resolveSessionPrimaryActionState } from "./InboxPanel.helpers.js";

function SessionCard({
  isActive = false,
  mode = "notes",
  onDeleteSession,
  onGenerateReport,
  onRenameSession,
  onReprocessSession,
  onSelect,
  reportStatus,
  session,
}) {
  const [menuOpen, setMenuOpen] = useState(false);
  const [menuPosition, setMenuPosition] = useState(null);
  const menuButtonRef = useRef(null);
  const menuRef = useRef(null);
  const { primaryActionDisabled, primaryActionLabel, workflow } =
    resolveSessionPrimaryActionState({ mode, reportStatus, session });
  const primaryAction = mode === "recaps" ? onGenerateReport : onReprocessSession;

  function updateMenuPosition() {
    const button = menuButtonRef.current;
    if (!button) {
      return;
    }

    const rect = button.getBoundingClientRect();
    setMenuPosition({
      right: Math.max(12, window.innerWidth - rect.right),
      top: Math.max(12, Math.min(rect.bottom + 6, window.innerHeight - 136)),
    });
  }

  useEffect(() => {
    if (!menuOpen) {
      return undefined;
    }

    updateMenuPosition();

    function handlePointerDown(event) {
      if (!menuRef.current?.contains(event.target)) {
        setMenuOpen(false);
      }
    }

    function handleViewportChange() {
      updateMenuPosition();
    }

    document.addEventListener("mousedown", handlePointerDown);
    window.addEventListener("resize", handleViewportChange);
    window.addEventListener("scroll", handleViewportChange, true);
    return () => {
      document.removeEventListener("mousedown", handlePointerDown);
      window.removeEventListener("resize", handleViewportChange);
      window.removeEventListener("scroll", handleViewportChange, true);
    };
  }, [menuOpen]);

  function handleMenuAction(action) {
    setMenuOpen(false);
    if (!action) {
      return;
    }
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
          onClick={() => {
            updateMenuPosition();
            setMenuOpen((current) => !current);
          }}
          ref={menuButtonRef}
          type="button"
        >
          <MoreHorizontal size={15} />
        </button>

        {menuOpen ? (
          <div
            className="caps-session-menu-dropdown"
            style={
              menuPosition
                ? {
                    right: `${menuPosition.right}px`,
                    top: `${menuPosition.top}px`,
                  }
                : undefined
            }
          >
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
              disabled={primaryActionDisabled}
              onClick={() => handleMenuAction(primaryAction)}
              type="button"
            >
              <RefreshCcw size={14} />
              {primaryActionLabel}
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

export function SessionSection({
  emptyCopy,
  isLive = false,
  items,
  mode,
  onDeleteSession,
  onGenerateReport,
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
            mode={mode}
            onDeleteSession={onDeleteSession}
            onGenerateReport={onGenerateReport}
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
