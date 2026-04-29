import React from "react";
import { AlertCircle, Loader } from "lucide-react";

import { WORKSPACE_MODES } from "../../app/workspace-modes.js";
import Assistant from "../../features/assistant/Assistant.jsx";
import Overview from "../../features/overview/Overview.jsx";
import Schedule from "../../features/schedule/Schedule.jsx";
import WorkspaceCanvas from "../../features/workspace/WorkspaceCanvas.jsx";
import WorkbenchPlaceholder from "./WorkbenchPlaceholder.jsx";

export default function WorkbenchRoute({
  activeMode,
  error,
  grouped,
  loading,
  onOpenDetail,
  onOpenLiveSession,
  onOpenSession,
  onOpenSessionInMode,
  onRefreshWorkspace,
  onViewRecaps,
  onViewSchedule,
  searchQuery,
  selectedSessionId,
  workspaceData,
  workspaceRefreshToken,
}) {
  const defaultLiveSessionId = selectedSessionId ?? grouped.running?.[0]?.id ?? null;
  const defaultRecapSessionId =
    selectedSessionId ?? grouped.ready?.[0]?.id ?? grouped.completed?.[0]?.id ?? null;

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
    case WORKSPACE_MODES.live:
      return defaultLiveSessionId ? (
        <WorkspaceCanvas
          onRefreshWorkspace={onRefreshWorkspace}
          refreshToken={workspaceRefreshToken}
          sessionId={defaultLiveSessionId}
          viewMode="live"
        />
      ) : (
        <WorkbenchPlaceholder />
      );
    case WORKSPACE_MODES.recaps:
    default:
      return defaultRecapSessionId ? (
        <WorkspaceCanvas
          onOpenDetail={onOpenDetail}
          onRefreshWorkspace={onRefreshWorkspace}
          refreshToken={workspaceRefreshToken}
          sessionId={defaultRecapSessionId}
          viewMode="recaps"
        />
      ) : (
        <WorkbenchPlaceholder />
      );
  }
}
