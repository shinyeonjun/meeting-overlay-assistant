import React, { useState } from "react";

import NavigationRail from "./NavigationRail.jsx";
import InboxPanel from "./InboxPanel.jsx";
import WorkbenchHeader from "./WorkbenchHeader.jsx";
import WorkbenchRoute from "./WorkbenchRoute.jsx";
import DetailPanel from "../shared/DetailPanel.jsx";
import { WORKSPACE_MODES } from "../../app/workspace-modes.js";
import useSessionCommands from "./hooks/useSessionCommands.js";
import useWorkspaceShellData from "./hooks/useWorkspaceShellData.js";
import "../../styles/app.css";

export default function Shell() {
  const [activeMode, setActiveMode] = useState(WORKSPACE_MODES.home);
  const [detailView, setDetailView] = useState(null);
  const [searchQuery, setSearchQuery] = useState("");
  const {
    error,
    grouped,
    loading,
    refreshWorkspace,
    reportStatuses,
    selectedSessionId,
    sessions,
    setSelectedSessionId,
    setWorkspaceData,
    workspaceData,
    workspaceRefreshToken,
  } = useWorkspaceShellData(activeMode);
  const {
    deleteSelectedSession,
    openSession,
    renameSelectedSession,
    reprocessSelectedSession,
  } = useSessionCommands({
    detailView,
    onRefreshWorkspace: refreshWorkspace,
    selectedSessionId,
    setActiveMode,
    setDetailView,
    setSelectedSessionId,
    setWorkspaceData,
  });

  const isAssistantMode = activeMode === WORKSPACE_MODES.assistant;
  const isMeetingsMode = activeMode === WORKSPACE_MODES.meetings;

  return (
    <div className="caps-workspace-shell">
      <WorkbenchHeader
        activeMode={activeMode}
        failedCount={grouped.failed?.length ?? 0}
        onRefresh={refreshWorkspace}
        onSearchChange={setSearchQuery}
        onSelectMode={setActiveMode}
        searchQuery={searchQuery}
      />

      <div className="caps-workspace-body">
        <NavigationRail activeMode={activeMode} setActiveMode={setActiveMode} />

        <main
          className={`caps-workspace-main ${isAssistantMode ? "assistant-mode" : ""} ${isMeetingsMode ? "meetings-mode" : ""}`}
        >
          {!isAssistantMode ? (
            <InboxPanel
              onDeleteSession={deleteSelectedSession}
              onRenameSession={renameSelectedSession}
              onReprocessSession={reprocessSelectedSession}
              onSelectSession={openSession}
              reportStatuses={reportStatuses}
              searchQuery={searchQuery}
              selectedSessionId={selectedSessionId}
              sessions={sessions}
            />
          ) : null}

          <section className="caps-workbench-surface">
            <WorkbenchRoute
              activeMode={activeMode}
              error={error}
              grouped={grouped}
              loading={loading}
              onOpenDetail={setDetailView}
              onOpenSession={openSession}
              onRefreshWorkspace={refreshWorkspace}
              onViewMeetings={() => setActiveMode(WORKSPACE_MODES.meetings)}
              selectedSessionId={selectedSessionId}
              workspaceData={workspaceData}
              workspaceRefreshToken={workspaceRefreshToken}
            />
          </section>
        </main>
      </div>

      <DetailPanel config={detailView} onClose={() => setDetailView(null)} />
    </div>
  );
}
