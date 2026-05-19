import React from "react";
import { AlertCircle, Loader } from "lucide-react";

import { WORKSPACE_MODES } from "../../app/workspace-modes.js";
import Assistant from "../../features/assistant/Assistant.jsx";
import Overview from "../../features/overview/Overview.jsx";
import Schedule from "../../features/schedule/Schedule.jsx";
import { SessionWorkbench } from "./WorkbenchRoute.parts.jsx";

export default function WorkbenchRoute({
  activeMode,
  error,
  grouped,
  loading,
  onDeleteSession,
  onGenerateReport,
  onOpenDetail,
  onOpenLiveSession,
  onOpenSession,
  onOpenSessionInMode,
  onRefreshWorkspace,
  onRenameSession,
  onReprocessSession,
  onViewRecaps,
  onViewSchedule,
  searchQuery,
  selectedSessionId,
  sessions,
  workspaceData,
  workspaceRefreshToken,
}) {
  if (loading) {
    return (
      <div className="workspace-state-view">
        <Loader className="spinner" size={28} />
        <p>워크스페이스를 불러오는 중입니다.</p>
      </div>
    );
  }

  if (error) {
    return (
      <div className="workspace-state-view error">
        <AlertCircle size={28} />
        <h3>워크스페이스를 열 수 없습니다.</h3>
        <p>{error}</p>
      </div>
    );
  }

  switch (activeMode) {
    case WORKSPACE_MODES.overview:
      return (
        <Overview
          data={workspaceData}
          grouped={grouped}
          onOpenDetail={onOpenDetail}
          onOpenLiveSession={onOpenLiveSession}
          onOpenSession={onOpenSession}
          onViewRecaps={onViewRecaps}
          onViewSchedule={onViewSchedule}
        />
      );
    case WORKSPACE_MODES.schedule:
      return (
        <Schedule
          data={workspaceData}
          grouped={grouped}
          onOpenLiveSession={onOpenLiveSession}
          onOpenSession={onOpenSession}
          reportStatuses={workspaceData?.reportStatuses ?? {}}
          searchQuery={searchQuery}
        />
      );
    case WORKSPACE_MODES.assistant:
      return (
        <Assistant
          initialBrief={workspaceData?.retrieval_brief}
          onOpenDetail={onOpenDetail}
          onOpenSession={onOpenSession}
          searchScope={{
            accountId: workspaceData?.account_id,
            contactId: workspaceData?.contact_id,
            contextThreadId: workspaceData?.context_thread_id,
          }}
        />
      );
    case WORKSPACE_MODES.recaps:
      return (
        <SessionWorkbench
          grouped={grouped}
          mode={WORKSPACE_MODES.recaps}
          onDeleteSession={onDeleteSession}
          onGenerateReport={onGenerateReport}
          onOpenDetail={onOpenDetail}
          onOpenSessionInMode={onOpenSessionInMode}
          onRefreshWorkspace={onRefreshWorkspace}
          onRenameSession={onRenameSession}
          onReprocessSession={onReprocessSession}
          reportStatuses={workspaceData?.reportStatuses ?? {}}
          searchQuery={searchQuery}
          selectedSessionId={selectedSessionId}
          sessions={sessions}
          workspaceRefreshToken={workspaceRefreshToken}
        />
      );
    case WORKSPACE_MODES.notes:
    default:
      return (
        <SessionWorkbench
          grouped={grouped}
          mode={WORKSPACE_MODES.notes}
          onDeleteSession={onDeleteSession}
          onGenerateReport={onGenerateReport}
          onOpenDetail={onOpenDetail}
          onOpenSessionInMode={onOpenSessionInMode}
          onRefreshWorkspace={onRefreshWorkspace}
          onRenameSession={onRenameSession}
          onReprocessSession={onReprocessSession}
          reportStatuses={workspaceData?.reportStatuses ?? {}}
          searchQuery={searchQuery}
          selectedSessionId={selectedSessionId}
          sessions={sessions}
          workspaceRefreshToken={workspaceRefreshToken}
        />
      );
  }
}
