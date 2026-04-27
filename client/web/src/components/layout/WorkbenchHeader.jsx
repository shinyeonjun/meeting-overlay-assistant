import React from "react";
import {
  RefreshCw,
  Search,
  Sparkles,
} from "lucide-react";

import {
  WORKSPACE_MODE_COPY,
  WORKSPACE_MODES,
} from "../../app/workspace-modes.js";

export default function WorkbenchHeader({
  activeMode,
  failedCount = 0,
  onRefresh,
  onSearchChange,
  onSelectMode,
  searchQuery,
}) {
  const modeCopy =
    WORKSPACE_MODE_COPY[activeMode] ?? WORKSPACE_MODE_COPY[WORKSPACE_MODES.home];
  const showWorkspaceSearch = activeMode !== WORKSPACE_MODES.assistant;

  return (
    <header className="caps-global-header">
      <div className="caps-global-header-left">
        <strong className="caps-brand">CAPS</strong>
        <div className="caps-header-context">
          <span>{modeCopy.title}</span>
          <p>{modeCopy.description}</p>
        </div>
      </div>

      <div className="caps-global-header-right">
        {showWorkspaceSearch ? (
          <label className="caps-global-search">
            <Search size={16} />
            <input
              onChange={(event) => onSearchChange(event.target.value)}
              placeholder="회의 검색..."
              type="text"
              value={searchQuery}
            />
          </label>
        ) : null}

        <div className="caps-global-actions">
          <button className="caps-icon-button" onClick={onRefresh} title="새로고침" type="button">
            <RefreshCw size={16} />
          </button>
        </div>

        {failedCount > 0 ? (
          <button
            className="caps-warning-button"
            onClick={() => onSelectMode(WORKSPACE_MODES.meetings)}
            type="button"
          >
            <Sparkles size={15} />
            확인 필요 {failedCount}건
          </button>
        ) : null}
      </div>
    </header>
  );
}
