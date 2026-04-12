/** 웹 공용 UI에서 Header 컴포넌트를 제공한다. */
import React from "react";
import { RefreshCw } from "lucide-react";

export default function Header({ title, subtitle, grouped, onRefresh }) {
  return (
    <header className="workspace-header">
      <div className="workspace-header-copy">
        <span className="workspace-header-eyebrow">WORKSPACE</span>
        <h1>{title}</h1>
        <p>{subtitle}</p>
      </div>

      <div className="workspace-header-actions">
        <div className="workspace-header-statusline">
          진행 중 {grouped.running.length} · 생성 가능 {grouped.ready.length} · 완료 {grouped.completed.length}
        </div>
        <button className="header-refresh-button" onClick={onRefresh} type="button">
          <RefreshCw size={16} />
          새로고침
        </button>
      </div>
    </header>
  );
}
