import React from "react";
import {
  Bell,
  HelpCircle,
  Plus,
  UserRound,
} from "lucide-react";

export default function WorkbenchHeader({
  activeMode,
  onSelectMode,
  onOpenReports,
}) {
  return (
    <header className="workspace-topbar">
      <div className="workspace-topbar-left">
        <h1>Meeting Intelligence</h1>
        <nav className="workspace-topbar-tabs">
          <button
            className={`workspace-topbar-tab ${activeMode === "sessions" ? "active" : ""}`}
            onClick={() => onSelectMode("sessions")}
            type="button"
          >
            Sessions
          </button>
          <button
            className={`workspace-topbar-tab ${activeMode === "assistant" ? "active" : ""}`}
            onClick={() => onSelectMode("assistant")}
            type="button"
          >
            Assistant
          </button>
        </nav>
      </div>

      <div className="workspace-topbar-right">
        <button className="workspace-topbar-primary" onClick={onOpenReports} type="button">
          <Plus size={14} />
          리포트 생성
        </button>
        <button className="workspace-topbar-icon" type="button">
          <Bell size={16} />
        </button>
        <button className="workspace-topbar-icon" type="button">
          <HelpCircle size={16} />
        </button>
        <div className="workspace-topbar-avatar">
          <UserRound size={15} />
        </div>
      </div>
    </header>
  );
}
