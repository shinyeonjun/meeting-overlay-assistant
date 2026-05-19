import React from "react";
import {
  AlertTriangle,
  Bell,
  Menu,
  RefreshCw,
  Search,
  Settings,
} from "lucide-react";

import { WORKSPACE_MODES } from "../../app/workspace-modes.js";

const SEARCH_PLACEHOLDER = {
  [WORKSPACE_MODES.overview]: "회의, 노트, 회의록 검색...",
  [WORKSPACE_MODES.notes]: "노트로 확인할 회의 검색...",
  [WORKSPACE_MODES.recaps]: "회의록을 만들거나 내려받을 회의 검색...",
  [WORKSPACE_MODES.assistant]: "회의 내용 질문하기...",
  [WORKSPACE_MODES.schedule]: "일정과 예정 회의 검색...",
};

export default function WorkbenchHeader({
  activeMode,
  failedCount = 0,
  mobileMenuOpen = false,
  onRefresh,
  onSearchChange,
  onSelectMode,
  onToggleMobileMenu,
  searchQuery,
}) {
  const placeholder = SEARCH_PLACEHOLDER[activeMode] ?? SEARCH_PLACEHOLDER[WORKSPACE_MODES.overview];

  return (
    <header className="caps-global-header">
      <div className="caps-global-header-left">
        <button
          aria-expanded={mobileMenuOpen}
          aria-label="메뉴 열기"
          className="caps-mobile-menu-button"
          onClick={onToggleMobileMenu}
          title="메뉴"
          type="button"
        >
          <Menu size={18} />
        </button>
        <strong className="caps-brand">CAPS</strong>
      </div>

      <div className="caps-global-header-right">
        <label className="caps-global-search">
          <Search size={16} />
          <input
            onChange={(event) => onSearchChange(event.target.value)}
            placeholder={placeholder}
            type="text"
            value={searchQuery}
          />
        </label>

        <div className="caps-global-actions">
          <button className="caps-icon-button" onClick={onRefresh} title="새로고침" type="button">
            <RefreshCw size={16} />
          </button>
          <button className="caps-icon-button" title="알림" type="button">
            <Bell size={16} />
          </button>
          <button className="caps-icon-button" title="설정" type="button">
            <Settings size={16} />
          </button>
        </div>

        {failedCount > 0 ? (
          <button
            className="caps-warning-button"
            onClick={() => onSelectMode(WORKSPACE_MODES.notes)}
            type="button"
          >
            <AlertTriangle size={15} />
            {failedCount}
          </button>
        ) : null}
        <button className="caps-user-avatar" title="프로필" type="button">C</button>
      </div>
    </header>
  );
}
