import React from "react";
import {
  Blocks,
  FileText,
  LayoutDashboard,
  Presentation,
  Settings,
} from "lucide-react";

const ITEMS = [
  { id: "sessions", label: "Sessions", icon: LayoutDashboard },
  { id: "history", label: "History", icon: Presentation },
  { id: "reports", label: "Reports", icon: FileText },
  { id: "assistant", label: "Assistant", icon: Blocks },
];

export default function NavigationRail({ activeMode, setActiveMode }) {
  return (
    <aside className="navigation-rail">
      <div className="rail-brand-mark rail-brand-mark-compact">C</div>

      <nav className="rail-nav">
        {ITEMS.map((item) => {
          const Icon = item.icon;
          const isActive = activeMode === item.id;
          return (
            <button
              key={item.id}
              className={`rail-nav-item ${isActive ? "active" : ""}`}
              onClick={() => setActiveMode(item.id)}
              type="button"
            >
              <Icon size={18} />
              <span>{item.label}</span>
            </button>
          );
        })}
      </nav>

      <div className="rail-footer">
        <button className="rail-nav-item rail-nav-item-footer" type="button">
          <Settings size={16} />
          <span>Settings</span>
        </button>
      </div>
    </aside>
  );
}
