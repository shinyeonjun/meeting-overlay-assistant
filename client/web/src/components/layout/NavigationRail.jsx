import React from "react";
import {
  Home,
  MessageSquareText,
  Mic,
} from "lucide-react";

import { WORKSPACE_MODES } from "../../app/workspace-modes.js";

const NAV_ITEMS = [
  { id: WORKSPACE_MODES.home, label: "홈", icon: Home },
  { id: WORKSPACE_MODES.meetings, label: "회의", icon: Mic },
  { id: WORKSPACE_MODES.assistant, label: "챗봇", icon: MessageSquareText },
];

export default function NavigationRail({ activeMode, setActiveMode }) {
  return (
    <aside className="caps-side-nav">
      <div className="caps-side-brand">
        <div className="caps-side-brand-mark">C</div>
        <div className="caps-side-brand-copy">
          <strong>CAPS</strong>
          <span>회의 정리</span>
        </div>
      </div>

      <div className="caps-side-section-label">작업 흐름</div>
      <nav className="caps-side-menu">
        {NAV_ITEMS.map((item) => {
          const Icon = item.icon;
          const isActive = activeMode === item.id;
          return (
            <button
              key={item.id}
              className={`caps-side-link ${isActive ? "active" : ""}`}
              onClick={() => setActiveMode(item.id)}
              type="button"
            >
              <Icon size={17} />
              <span>{item.label}</span>
            </button>
          );
        })}
      </nav>
    </aside>
  );
}
