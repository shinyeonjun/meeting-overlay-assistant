import React from "react";
import {
  CalendarDays,
  LayoutDashboard,
  MessageSquareText,
  NotebookText,
  Plus,
  ScrollText,
} from "lucide-react";

import { WORKSPACE_MODES } from "../../app/workspace-modes.js";

const SIDEBAR_ITEMS = [
  { id: WORKSPACE_MODES.overview, label: "대시보드", icon: LayoutDashboard },
  { id: WORKSPACE_MODES.notes, label: "노트", icon: NotebookText },
  { id: WORKSPACE_MODES.recaps, label: "회의록", icon: ScrollText },
  { id: WORKSPACE_MODES.assistant, label: "챗봇", icon: MessageSquareText },
  { id: WORKSPACE_MODES.schedule, label: "일정", icon: CalendarDays },
];

export function StitchSidebar({
  activeMode,
  mobileMenuOpen,
  onCloseMobileMenu,
  onSelectMode,
}) {
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
        onClick={() => selectMode(WORKSPACE_MODES.notes)}
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
