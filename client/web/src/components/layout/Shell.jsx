import React, { useEffect, useMemo, useState } from "react";
import { AlertCircle, Loader } from "lucide-react";

import NavigationRail from "./NavigationRail.jsx";
import InboxPanel from "./InboxPanel.jsx";
import WorkbenchHeader from "./WorkbenchHeader.jsx";
import WorkbenchPlaceholder from "./WorkbenchPlaceholder.jsx";
import DetailPanel from "../shared/DetailPanel.jsx";
import Assistant from "../../features/assistant/Assistant.jsx";
import History from "../../features/history/History.jsx";
import Reports from "../../features/reports/Reports.jsx";
import WorkspaceCanvas from "../../features/workspace/WorkspaceCanvas.jsx";
import { fetchWorkspaceOverview } from "../../services/workspace-api.js";
import {
  groupSessionsByOperationalState,
  sortSessionsByStartedAt,
} from "../../app/workspace-model.js";
import "../../styles/app.css";

function selectDefaultSession(grouped, sessions) {
  return (
    grouped.running?.[0]?.id ||
    grouped.ready?.[0]?.id ||
    grouped.processing?.[0]?.id ||
    grouped.failed?.[0]?.id ||
    sessions?.[0]?.id ||
    null
  );
}

function getWorkspaceLoadOptions(activeMode) {
  switch (activeMode) {
    case "history":
      return {
        scope: "all",
        limit: 24,
        includeReports: true,
        includeCarryOver: true,
        includeRetrievalBrief: false,
      };
    case "reports":
      return {
        scope: "all",
        limit: 24,
        includeReports: true,
        includeCarryOver: false,
        includeRetrievalBrief: false,
      };
    case "assistant":
      return {
        scope: "all",
        limit: 24,
        includeReports: false,
        includeCarryOver: false,
        includeRetrievalBrief: true,
      };
    case "sessions":
    default:
      return {
        scope: "all",
        limit: 24,
        includeReports: false,
        includeCarryOver: false,
        includeRetrievalBrief: false,
      };
  }
}

function getHeaderCopy({ activeMode, selectedSession }) {
  switch (activeMode) {
    case "history":
      return {
        title: "세션 기록 보드",
        subtitle:
          "종료된 회의와 최신 리포트를 같은 흐름에서 다시 확인하는 기록 작업면입니다.",
      };
    case "reports":
      return {
        title: "리포트 생성 큐",
        subtitle:
          "자동 생성 대신 운영자가 직접 생성하고 재시도하는 문서 작업 큐입니다.",
      };
    case "assistant":
      return {
        title: "검색 워크벤치",
        subtitle:
          "세션과 리포트에서 근거를 다시 찾고, 후속 질문에 필요한 단서를 모으는 공간입니다.",
      };
    case "sessions":
    default:
      return {
        title: selectedSession?.title || "Session Review Desk",
        subtitle: selectedSession
          ? "선택한 회의의 상태, 최신 리포트, 다음 작업을 하나의 검토면에서 이어서 봅니다."
          : "왼쪽 인박스에서 세션을 고르면 여기서 바로 검토와 문서 작업을 이어갈 수 있습니다.",
      };
  }
}

export default function Shell() {
  const [activeMode, setActiveMode] = useState("sessions");
  const [workspaceData, setWorkspaceData] = useState(null);
  const [selectedSessionId, setSelectedSessionId] = useState();
  const [detailView, setDetailView] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  async function loadWorkspaceData(mode) {
    const overview = await fetchWorkspaceOverview(getWorkspaceLoadOptions(mode));
    return {
      ...overview,
      reportStatuses: overview.report_statuses ?? {},
    };
  }

  useEffect(() => {
    let cancelled = false;

    async function boot() {
      try {
        setLoading(true);
        setError(null);
        const nextData = await loadWorkspaceData(activeMode);
        if (!cancelled) {
          setWorkspaceData(nextData);
        }
      } catch (nextError) {
        if (!cancelled) {
          setError(
            nextError instanceof Error
              ? nextError.message
              : "워크스페이스를 불러오지 못했습니다.",
          );
        }
      } finally {
        if (!cancelled) {
          setLoading(false);
        }
      }
    }

    void boot();
    return () => {
      cancelled = true;
    };
  }, [activeMode]);

  const sessions = useMemo(
    () => sortSessionsByStartedAt(workspaceData?.sessions ?? []),
    [workspaceData],
  );

  const reportStatuses = workspaceData?.reportStatuses ?? {};
  const reports = workspaceData?.reports ?? [];
  const retrievalItems = workspaceData?.retrieval_brief?.items ?? [];
  const retrievalScope = useMemo(
    () => ({
      accountId: workspaceData?.account_id ?? undefined,
      contactId: workspaceData?.contact_id ?? undefined,
      contextThreadId: workspaceData?.context_thread_id ?? undefined,
    }),
    [workspaceData?.account_id, workspaceData?.contact_id, workspaceData?.context_thread_id],
  );

  const grouped = useMemo(
    () => groupSessionsByOperationalState(sessions, reportStatuses),
    [sessions, reportStatuses],
  );

  useEffect(() => {
    if (selectedSessionId === undefined || (selectedSessionId === null && activeMode === "sessions")) {
      setSelectedSessionId(selectDefaultSession(grouped, sessions));
      return;
    }

    if (selectedSessionId === null) {
      return;
    }

    const stillExists = sessions.some((session) => session.id === selectedSessionId);
    if (!stillExists) {
      setSelectedSessionId(selectDefaultSession(grouped, sessions));
    }
  }, [activeMode, grouped, sessions, selectedSessionId]);

  const selectedSession = useMemo(
    () => sessions.find((session) => session.id === selectedSessionId) ?? null,
    [sessions, selectedSessionId],
  );

  const { title: headerTitle, subtitle: headerSubtitle } = getHeaderCopy({
    activeMode,
    selectedSession,
  });

  async function handleRefresh() {
    try {
      setLoading(true);
      setError(null);
      const nextData = await loadWorkspaceData(activeMode);
      setWorkspaceData(nextData);
    } catch (nextError) {
      setError(
        nextError instanceof Error ? nextError.message : "새로고침에 실패했습니다.",
      );
    } finally {
      setLoading(false);
    }
  }

  function handleOpenSession(sessionId) {
    setSelectedSessionId(sessionId);
    setActiveMode("sessions");
  }

  function handleOpenReport(report) {
    setDetailView({
      type: "report",
      sessionId: report.session_id,
      reportId: report.id,
    });
  }

  function handleOpenRetrieval(item) {
    if (item.report_id) {
      setDetailView({
        type: "report",
        sessionId: item.session_id,
        reportId: item.report_id,
      });
      return;
    }

    if (item.session_id) {
      handleOpenSession(item.session_id);
    }
  }

  let workbench = null;
  if (loading) {
    workbench = (
      <div className="workspace-state-view">
        <Loader className="spinner" size={28} />
        <p>워크스페이스를 불러오는 중입니다.</p>
      </div>
    );
  } else if (error) {
    workbench = (
      <div className="workspace-state-view error">
        <AlertCircle size={28} />
        <h3>워크스페이스를 열지 못했습니다.</h3>
        <p>{error}</p>
      </div>
    );
  } else {
    switch (activeMode) {
      case "history":
        workbench = (
          <History
            data={workspaceData}
            onOpenSession={handleOpenSession}
            onOpenDetail={setDetailView}
          />
        );
        break;
      case "reports":
        workbench = (
          <Reports
            data={workspaceData}
            grouped={grouped}
            onOpenSession={handleOpenSession}
            onOpenDetail={setDetailView}
            onRefreshWorkspace={handleRefresh}
          />
        );
        break;
      case "assistant":
        workbench = (
          <Assistant
            initialBrief={workspaceData?.retrieval_brief}
            searchScope={retrievalScope}
            onOpenSession={handleOpenSession}
            onOpenDetail={setDetailView}
          />
        );
        break;
      case "sessions":
      default:
        workbench = selectedSessionId ? (
          <WorkspaceCanvas
            sessionId={selectedSessionId}
            onOpenDetail={setDetailView}
            onRefreshWorkspace={handleRefresh}
          />
        ) : (
          <WorkbenchPlaceholder />
        );
        break;
    }
  }

  return (
    <div className="workspace-shell workspace-shell-stitch">
      <NavigationRail activeMode={activeMode} setActiveMode={setActiveMode} />

      <div className="workspace-main-shell">
        <WorkbenchHeader
          activeMode={activeMode}
          onOpenReports={() => setActiveMode("reports")}
          onSelectMode={setActiveMode}
        />

        <div className="workspace-main-body">
          <aside className="workspace-queue-column">
            <InboxPanel
              activeMode={activeMode}
              grouped={grouped}
              sessions={sessions}
              reports={reports}
              reportStatuses={reportStatuses}
              retrievalBrief={retrievalItems}
              selectedSessionId={selectedSessionId}
              onSelectSession={handleOpenSession}
              onOpenReport={handleOpenReport}
              onOpenRetrieval={handleOpenRetrieval}
            />
          </aside>

          <section
            className={`workspace-review-column ${activeMode === "sessions" ? "sessions-mode" : "generic-mode"}`}
          >
            {activeMode === "sessions" ? (
              <div className="workspace-workbench-body">{workbench}</div>
            ) : (
              <>
                <div className="workspace-review-head">
                  <span className="section-kicker">{headerTitle}</span>
                  <p>{headerSubtitle}</p>
                </div>
                <div className="workspace-workbench-body">{workbench}</div>
              </>
            )}
          </section>
        </div>
      </div>

      <DetailPanel config={detailView} onClose={() => setDetailView(null)} />
    </div>
  );
}
