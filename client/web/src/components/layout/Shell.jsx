import React, { useState } from "react";
import {
  Bot,
  CalendarDays,
  FileText,
  LayoutDashboard,
  Plus,
  Video,
} from "lucide-react";

import WorkbenchHeader from "./WorkbenchHeader.jsx";
import WorkbenchRoute from "./WorkbenchRoute.jsx";
import DetailPanel from "../shared/DetailPanel.jsx";
import { WORKSPACE_MODES } from "../../app/workspace-modes.js";
import useSessionCommands from "./hooks/useSessionCommands.js";
import useWorkspaceShellData from "./hooks/useWorkspaceShellData.js";
import "../../styles/app.css";

const SIDEBAR_ITEMS = [
  { id: WORKSPACE_MODES.overview, label: "대시보드", icon: LayoutDashboard },
  { id: WORKSPACE_MODES.schedule, label: "일정", icon: CalendarDays },
  { id: WORKSPACE_MODES.live, label: "실시간 회의", icon: Video },
  { id: WORKSPACE_MODES.recaps, label: "회의록", icon: FileText },
  { id: WORKSPACE_MODES.assistant, label: "어시스턴트", icon: Bot },
];

function StitchSidebar({ activeMode, mobileMenuOpen, onCloseMobileMenu, onSelectMode }) {
  function selectMode(mode) {
    onSelectMode(mode);
    onCloseMobileMenu();
  }

  return (
    <aside className={`caps-stitch-sidebar ${mobileMenuOpen ? "open" : ""}`}>
      <div className="caps-stitch-brand-block">
        <div className="caps-stitch-brand-mark">C</div>
        <div>
          <strong>CAPS</strong>
          <span>회의 워크스페이스</span>
        </div>
      </div>

      <button
        className="caps-stitch-new-meeting"
        onClick={() => selectMode(WORKSPACE_MODES.live)}
        type="button"
      >
        <Plus size={18} />
        새 회의 시작
      </button>

      <nav className="caps-stitch-nav" aria-label="CAPS 워크스페이스">
        {SIDEBAR_ITEMS.map((item) => {
          const Icon = item.icon;
          return (
            <button
              key={item.id}
              className={`caps-stitch-nav-link ${activeMode === item.id ? "active" : ""}`}
              onClick={() => selectMode(item.id)}
              type="button"
            >
              <Icon size={19} />
              {item.label}
            </button>
          );
        })}
      </nav>

    </aside>
  );
}

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

  function openSessionInMode(sessionId, mode = WORKSPACE_MODES.recaps) {
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
            onOpenDetail={setDetailView}
            onOpenLiveSession={(sessionId) => openSessionInMode(sessionId, WORKSPACE_MODES.live)}
            onOpenSession={openSession}
            onOpenSessionInMode={openSessionInMode}
            onRefreshWorkspace={refreshWorkspace}
            onViewRecaps={() => setActiveMode(WORKSPACE_MODES.recaps)}
            onViewSchedule={() => setActiveMode(WORKSPACE_MODES.schedule)}
            searchQuery={searchQuery}
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
