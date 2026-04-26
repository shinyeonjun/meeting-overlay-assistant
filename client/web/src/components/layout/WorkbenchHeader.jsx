import React from "react";
import {
  NotebookPen,
  RefreshCw,
  Search,
  Share2,
  Sparkles,
} from "lucide-react";

const TAB_ITEMS = [
  { id: "meetings", label: "최근 회의" },
  { id: "operations", label: "분석 리포트" },
  { id: "home", label: "워크스페이스" },
];

export default function WorkbenchHeader({
  activeMode,
  failedCount = 0,
  onRefresh,
  onSearchChange,
  onSelectMode,
  searchQuery,
}) {
  return (
    <header className="caps-global-header">
      <div className="caps-global-header-left">
        <strong className="caps-brand">근거 기반 회의록</strong>
        <nav className="caps-header-tabs" aria-label="상단 메뉴">
          {TAB_ITEMS.map((item) => (
            <button
              key={item.id}
              className={`caps-header-tab ${activeMode === item.id ? "active" : ""}`}
              onClick={() => onSelectMode(item.id)}
              type="button"
            >
              {item.label}
            </button>
          ))}
        </nav>
      </div>

      <div className="caps-global-header-right">
        <label className="caps-global-search">
          <Search size={16} />
          <input
            onChange={(event) => onSearchChange(event.target.value)}
            placeholder="회의 검색..."
            type="text"
            value={searchQuery}
          />
        </label>

        <div className="caps-global-actions">
          <button className="caps-icon-button" onClick={onRefresh} title="새로고침" type="button">
            <RefreshCw size={16} />
          </button>
          <button className="caps-icon-button" title="메모" type="button">
            <NotebookPen size={16} />
          </button>
          <button className="caps-icon-button" title="공유" type="button">
            <Share2 size={16} />
          </button>
        </div>

        {failedCount > 0 ? (
          <button
            className="caps-warning-button"
            onClick={() => onSelectMode("operations")}
            type="button"
          >
            <Sparkles size={15} />
            확인 필요 {failedCount}건
          </button>
        ) : null}

        <button className="caps-login-button" type="button">
          로그아웃
        </button>
      </div>
    </header>
  );
}
