import React, { useMemo } from "react";

import {
  buildGroupedLists,
  filterSessions,
} from "./InboxPanel.helpers.js";
import { SessionSection } from "./InboxPanel.parts.jsx";

export default function InboxPanel({
  description = "회의를 선택하면 오른쪽에서 내용을 확인할 수 있습니다.",
  mode = "notes",
  onDeleteSession,
  onGenerateReport,
  onRenameSession,
  onReprocessSession,
  onSelectSession,
  reportStatuses,
  searchQuery,
  selectedSessionId,
  sessions,
  title = "회의 목록",
}) {
  const filteredSessions = useMemo(
    () => filterSessions(sessions, searchQuery),
    [searchQuery, sessions],
  );

  const { filteredActionNeeded, filteredRecent, filteredRunning } = useMemo(
    () => buildGroupedLists({ filteredSessions, reportStatuses }),
    [filteredSessions, reportStatuses],
  );

  const actionTitle = mode === "recaps" ? "회의록 확인 필요" : "정리 필요";
  const recentTitle = mode === "recaps" ? "최근 회의록" : "최근 노트";

  return (
    <section className="caps-session-list-panel">
      <div className="caps-session-list-header">
        <h2>{title}</h2>
        <p>{description}</p>
      </div>

      <div className="caps-session-list-scroll">
        <SessionSection
          emptyCopy="진행 중인 회의가 없습니다."
          isLive
          items={filteredRunning}
          mode={mode}
          onDeleteSession={onDeleteSession}
          onGenerateReport={onGenerateReport}
          onRenameSession={onRenameSession}
          onReprocessSession={onReprocessSession}
          onSelectSession={onSelectSession}
          reportStatuses={reportStatuses}
          selectedSessionId={selectedSessionId}
          title="진행 중"
        />

        <SessionSection
          emptyCopy={
            mode === "recaps"
              ? "회의록을 확인할 작업이 없습니다."
              : "다시 정리할 노트가 없습니다."
          }
          items={filteredActionNeeded}
          mode={mode}
          onDeleteSession={onDeleteSession}
          onGenerateReport={onGenerateReport}
          onRenameSession={onRenameSession}
          onReprocessSession={onReprocessSession}
          onSelectSession={onSelectSession}
          reportStatuses={reportStatuses}
          selectedSessionId={selectedSessionId}
          title={actionTitle}
        />

        <SessionSection
          emptyCopy="표시할 회의가 없습니다."
          items={filteredRecent}
          mode={mode}
          onDeleteSession={onDeleteSession}
          onGenerateReport={onGenerateReport}
          onRenameSession={onRenameSession}
          onReprocessSession={onReprocessSession}
          onSelectSession={onSelectSession}
          reportStatuses={reportStatuses}
          selectedSessionId={selectedSessionId}
          title={recentTitle}
        />
      </div>
    </section>
  );
}
