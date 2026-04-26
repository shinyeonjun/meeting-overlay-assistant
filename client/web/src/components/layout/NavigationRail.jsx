import React from "react";
import {
  CalendarDays,
  HelpCircle,
  Home,
  Mic,
  Settings,
} from "lucide-react";

const NAV_ITEMS = [
  { id: "home", label: "홈", icon: Home, mode: "home" },
  { id: "meetings", label: "회의", icon: Mic, mode: "meetings" },
  { id: "calendar", label: "캘린더", icon: CalendarDays, mode: null },
  { id: "settings", label: "설정", icon: Settings, mode: null },
];

export default function NavigationRail({ activeMode, setActiveMode }) {
  return (
    <aside className="caps-side-nav">
      <div className="caps-side-brand">
        <div className="caps-side-brand-mark">W</div>
        <div className="caps-side-brand-copy">
          <strong>회의 워크스페이스</strong>
          <span>근거 기반 회의록</span>
        </div>
      </div>

      <div className="caps-side-section-label">Main Menu</div>
      <nav className="caps-side-menu">
        {NAV_ITEMS.map((item) => {
          const Icon = item.icon;
          const isActive = item.mode ? activeMode === item.mode : false;
          return (
            <button
              key={item.id}
              className={`caps-side-link ${isActive ? "active" : ""}`}
              onClick={() => {
                if (item.mode) {
                  setActiveMode(item.mode);
                }
              }}
              type="button"
            >
              <Icon size={17} />
              <span>{item.label}</span>
            </button>
          );
        })}
      </nav>

      <div className="caps-side-footer">
        <button className="caps-side-link" type="button">
          <HelpCircle size={17} />
          <span>도움말</span>
        </button>
      </div>
    </aside>
  );
}
