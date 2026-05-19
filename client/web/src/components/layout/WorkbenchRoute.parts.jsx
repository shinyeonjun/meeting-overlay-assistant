import React from "react";

import { WORKSPACE_MODES } from "../../app/workspace-modes.js";
import WorkspaceCanvas from "../../features/workspace/WorkspaceCanvas.jsx";
import InboxPanel from "./InboxPanel.jsx";
import WorkbenchPlaceholder from "./WorkbenchPlaceholder.jsx";

function resolveDefaultSessionId({ grouped, selectedSessionId, sessions, viewMode }) {
  if (selectedSessionId) {
    return selectedSessionId;
  }
  if (viewMode === "recaps") {
    return grouped.ready?.[0]?.id ?? grouped.completed?.[0]?.id ?? sessions?.[0]?.id ?? null;
  }
  return (
    grouped.running?.[0]?.id ??
    grouped.processing?.[0]?.id ??
    grouped.completed?.[0]?.id ??
    grouped.ready?.[0]?.id ??
    sessions?.[0]?.id ??
    null
  );
}

export function SessionWorkbench({
  grouped,
  mode,
  onDeleteSession,
  onGenerateReport,
  onOpenDetail,
  onOpenSessionInMode,
  onRefreshWorkspace,
  onRenameSession,
  onReprocessSession,
  reportStatuses,
  searchQuery,
  selectedSessionId,
  sessions,
  workspaceRefreshToken,
}) {
  const viewMode = mode === WORKSPACE_MODES.recaps ? "recaps" : "live";
  const activeSessionId = resolveDefaultSessionId({
    grouped,
    selectedSessionId,
    sessions,
    viewMode,
  });
  const isRecapsMode = mode === WORKSPACE_MODES.recaps;

  return (
    <div className={`caps-session-workbench ${isRecapsMode ? "recaps-mode" : "notes-mode"} animate-fade-in`}>
      <InboxPanel
        description={
          isRecapsMode
            ? "회의를 선택해 회의록 생성, 편집, 다운로드를 처리합니다."
            : "회의를 선택해 노트, 전사 원문, 인사이트를 확인합니다."
        }
        mode={isRecapsMode ? "recaps" : "notes"}
        onDeleteSession={onDeleteSession}
        onGenerateReport={onGenerateReport}
        onRenameSession={onRenameSession}
        onReprocessSession={onReprocessSession}
        onSelectSession={(sessionId) => onOpenSessionInMode(sessionId, mode)}
        reportStatuses={reportStatuses}
        searchQuery={searchQuery}
        selectedSessionId={activeSessionId}
        sessions={sessions}
        title={isRecapsMode ? "회의록 선택" : "노트 선택"}
      />

      <div className="caps-session-detail-surface">
        {activeSessionId ? (
          <WorkspaceCanvas
            onOpenDetail={onOpenDetail}
            onRefreshWorkspace={onRefreshWorkspace}
            refreshToken={workspaceRefreshToken}
            sessionId={activeSessionId}
            viewMode={viewMode}
          />
        ) : (
          <WorkbenchPlaceholder />
        )}
      </div>
    </div>
  );
}
