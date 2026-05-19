import React, { useState } from "react";

import WorkbenchHeader from "./WorkbenchHeader.jsx";
import WorkbenchRoute from "./WorkbenchRoute.jsx";
import { StitchSidebar } from "./Shell.parts.jsx";
import DetailPanel from "../shared/DetailPanel.jsx";
import { WORKSPACE_MODES } from "../../app/workspace-modes.js";
import useSessionCommands from "./hooks/useSessionCommands.js";
import useWorkspaceShellData from "./hooks/useWorkspaceShellData.js";
import "../../styles/app.css";

export default function Shell() {
  const [activeMode, setActiveMode] = useState(WORKSPACE_MODES.overview);
  const [detailView, setDetailView] = useState(null);
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);
  const [searchQuery, setSearchQuery] = useState("");
  const {
    error,
    grouped,
    loading,
    refreshWorkspace,
    selectedSessionId,
    sessions,
    setSelectedSessionId,
    setWorkspaceData,
    workspaceData,
    workspaceRefreshToken,
  } = useWorkspaceShellData(activeMode);
  const {
    deleteSelectedSession,
    generateReportForSession,
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

  function openSessionInMode(sessionId, mode = WORKSPACE_MODES.notes) {
    setSelectedSessionId(sessionId);
    setActiveMode(mode);
    setMobileMenuOpen(false);
  }

  return (
    <div className="caps-product-shell caps-stitch-shell">
      <StitchSidebar
        activeMode={activeMode}
        mobileMenuOpen={mobileMenuOpen}
        onCloseMobileMenu={() => setMobileMenuOpen(false)}
        onSelectMode={setActiveMode}
      />
      <button
        aria-label="메뉴 닫기"
        className={`caps-stitch-sidebar-backdrop ${mobileMenuOpen ? "open" : ""}`}
        onClick={() => setMobileMenuOpen(false)}
        type="button"
      />

      <div className="caps-stitch-main">
        <WorkbenchHeader
          activeMode={activeMode}
          failedCount={grouped.failed?.length ?? 0}
          mobileMenuOpen={mobileMenuOpen}
          onRefresh={refreshWorkspace}
          onSearchChange={setSearchQuery}
          onSelectMode={setActiveMode}
          onToggleMobileMenu={() => setMobileMenuOpen((open) => !open)}
          searchQuery={searchQuery}
        />

        <main className={`caps-product-main mode-${activeMode}`}>
          <section className="caps-product-surface">
            <WorkbenchRoute
              activeMode={activeMode}
              error={error}
              grouped={grouped}
              loading={loading}
              onDeleteSession={deleteSelectedSession}
              onGenerateReport={generateReportForSession}
              onOpenDetail={setDetailView}
              onOpenLiveSession={(sessionId) => openSessionInMode(sessionId, WORKSPACE_MODES.notes)}
              onOpenSession={openSession}
              onOpenSessionInMode={openSessionInMode}
              onRefreshWorkspace={refreshWorkspace}
              onRenameSession={renameSelectedSession}
              onReprocessSession={reprocessSelectedSession}
              onViewRecaps={() => setActiveMode(WORKSPACE_MODES.recaps)}
              onViewSchedule={() => setActiveMode(WORKSPACE_MODES.schedule)}
              searchQuery={searchQuery}
              selectedSessionId={selectedSessionId}
              sessions={sessions}
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
