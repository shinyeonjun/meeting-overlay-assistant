/** 웹 공용 UI에서 Shell 컴포넌트를 제공한다. */
import React, { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { AlertCircle, Loader } from "lucide-react";

import NavigationRail from "./NavigationRail.jsx";
import InboxPanel from "./InboxPanel.jsx";
import WorkbenchHeader from "./WorkbenchHeader.jsx";
import WorkbenchPlaceholder from "./WorkbenchPlaceholder.jsx";
import DetailPanel from "../shared/DetailPanel.jsx";
import Overview from "../../features/overview/Overview.jsx";
import Reports from "../../features/reports/Reports.jsx";
import WorkspaceCanvas from "../../features/workspace/WorkspaceCanvas.jsx";
import { fetchWorkspaceOverview } from "../../services/workspace-api.js";
import {
  deleteSession,
  renameSession,
  reprocessSession,
} from "../../services/session-api.js";
import {
  groupSessionsByOperationalState,
  sortSessionsByStartedAt,
} from "../../app/workspace-model.js";
import "../../styles/app.css";

function selectDefaultSession(grouped, sessions) {
  return (
    grouped.running?.[0]?.id ||
    grouped.processing?.[0]?.id ||
    grouped.ready?.[0]?.id ||
    grouped.failed?.[0]?.id ||
    sessions?.[0]?.id ||
    null
  );
}

function getWorkspaceLoadOptions(activeMode) {
  switch (activeMode) {
    case "operations":
      return {
        scope: "all",
        limit: 24,
        includeReports: true,
        includeCarryOver: false,
        includeRetrievalBrief: false,
      };
    case "meetings":
      return {
        scope: "all",
        limit: 24,
        includeReports: true,
        includeCarryOver: false,
        includeRetrievalBrief: false,
      };
    case "home":
    default:
      return {
        scope: "all",
        limit: 16,
        includeReports: true,
        includeCarryOver: true,
        includeRetrievalBrief: false,
      };
  }
}

export default function Shell() {
  const startupRecoveryRefreshScheduledRef = useRef(false);
  const [activeMode, setActiveMode] = useState("meetings");
  const [workspaceData, setWorkspaceData] = useState(null);
  const [selectedSessionId, setSelectedSessionId] = useState();
  const [detailView, setDetailView] = useState(null);
  const [workspaceRefreshToken, setWorkspaceRefreshToken] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [searchQuery, setSearchQuery] = useState("");

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

  useEffect(() => {
    if (loading || workspaceData == null || startupRecoveryRefreshScheduledRef.current) {
      return undefined;
    }

    const hasRunningSessions = (workspaceData.sessions ?? []).some(
      (session) => String(session?.status ?? "").toLowerCase() === "running",
    );
    if (!hasRunningSessions) {
      return undefined;
    }

    startupRecoveryRefreshScheduledRef.current = true;
    let cancelled = false;
    const timerId = window.setTimeout(async () => {
      try {
        const nextData = await loadWorkspaceData(activeMode);
        if (!cancelled) {
          setWorkspaceData(nextData);
          setWorkspaceRefreshToken((current) => current + 1);
        }
      } catch {
        // startup 복구 후 목록 동기화는 최선 시도만 한다.
      }
    }, 3000);

    return () => {
      cancelled = true;
      window.clearTimeout(timerId);
    };
  }, [activeMode, loading, workspaceData]);

  const sessions = useMemo(
    () => sortSessionsByStartedAt(workspaceData?.sessions ?? []),
    [workspaceData],
  );
  const reportStatuses = workspaceData?.reportStatuses ?? {};
  const grouped = useMemo(
    () => groupSessionsByOperationalState(sessions, reportStatuses),
    [sessions, reportStatuses],
  );

  useEffect(() => {
    if (selectedSessionId === undefined) {
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
  }, [grouped, selectedSessionId, sessions]);

  const handleRefresh = useCallback(async (options = {}) => {
    const background = Boolean(options?.background);
    const syncSession = options?.syncSession !== false;
    try {
      if (!background) {
        setLoading(true);
      }
      setError(null);
      const nextData = await loadWorkspaceData(activeMode);
      setWorkspaceData(nextData);
      if (syncSession) {
        setWorkspaceRefreshToken((current) => current + 1);
      }
    } catch (nextError) {
      setError(
        nextError instanceof Error ? nextError.message : "새로고침에 실패했습니다.",
      );
    } finally {
      if (!background) {
        setLoading(false);
      }
    }
  }, [activeMode]);

  function handleOpenSession(sessionId) {
    setSelectedSessionId(sessionId);
    setActiveMode("meetings");
  }

  async function handleRenameSession(session) {
    const nextTitle = window.prompt("새 세션 이름을 입력하세요.", session.title ?? "");
    if (nextTitle === null) {
      return;
    }

    const normalizedTitle = nextTitle.trim();
    if (!normalizedTitle || normalizedTitle === session.title) {
      return;
    }

    try {
      await renameSession({ sessionId: session.id, title: normalizedTitle });
      await handleRefresh();
    } catch (nextError) {
      window.alert(
        nextError instanceof Error ? nextError.message : "세션 이름을 바꾸지 못했습니다.",
      );
    }
  }

  async function handleDeleteSession(session) {
    const confirmed = window.confirm(
      `"${session.title || "제목 없는 회의"}" 세션을 삭제할까요?`,
    );
    if (!confirmed) {
      return;
    }

    try {
      await deleteSession({ sessionId: session.id });
      if (selectedSessionId === session.id) {
        setSelectedSessionId(undefined);
      }
      if (detailView?.sessionId === session.id) {
        setDetailView(null);
      }
      await handleRefresh();
    } catch (nextError) {
      window.alert(
        nextError instanceof Error ? nextError.message : "세션을 삭제하지 못했습니다.",
      );
    }
  }

  async function handleReprocessSession(session) {
    try {
      const refreshedSession = await reprocessSession({ sessionId: session.id });
      setSelectedSessionId(session.id);
      setActiveMode("meetings");
      setWorkspaceData((current) => {
        if (!current) {
          return current;
        }
        return {
          ...current,
          sessions: (current.sessions ?? []).map((item) =>
            item.id === session.id ? { ...item, ...refreshedSession } : item,
          ),
        };
      });
      await handleRefresh({ background: true });
    } catch (nextError) {
      window.alert(
        nextError instanceof Error ? nextError.message : "노트 생성을 요청하지 못했습니다.",
      );
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
        <h3>워크스페이스를 열 수 없습니다.</h3>
        <p>{error}</p>
      </div>
    );
  } else {
    switch (activeMode) {
      case "home":
        workbench = (
          <Overview
            data={workspaceData}
            grouped={grouped}
            onOpenDetail={setDetailView}
            onOpenSession={handleOpenSession}
            onViewMeetings={() => setActiveMode("meetings")}
          />
        );
        break;
      case "operations":
        workbench = (
          <Reports
            data={workspaceData}
            grouped={grouped}
            onOpenDetail={setDetailView}
            onOpenSession={handleOpenSession}
            onRefreshWorkspace={handleRefresh}
          />
        );
        break;
      case "meetings":
      default:
        workbench = selectedSessionId ? (
          <WorkspaceCanvas
            onOpenDetail={setDetailView}
            onRefreshWorkspace={handleRefresh}
            refreshToken={workspaceRefreshToken}
            sessionId={selectedSessionId}
          />
        ) : (
          <WorkbenchPlaceholder />
        );
        break;
    }
  }

  return (
    <div className="caps-workspace-shell">
      <WorkbenchHeader
        activeMode={activeMode}
        failedCount={grouped.failed?.length ?? 0}
        onRefresh={handleRefresh}
        onSearchChange={setSearchQuery}
        onSelectMode={setActiveMode}
        searchQuery={searchQuery}
      />

      <div className="caps-workspace-body">
        <NavigationRail activeMode={activeMode} setActiveMode={setActiveMode} />

        <main className="caps-workspace-main">
          <InboxPanel
            grouped={grouped}
            onDeleteSession={handleDeleteSession}
            onRenameSession={handleRenameSession}
            onReprocessSession={handleReprocessSession}
            onSelectSession={handleOpenSession}
            reportStatuses={reportStatuses}
            searchQuery={searchQuery}
            selectedSessionId={selectedSessionId}
            sessions={sessions}
          />

          <section className="caps-workbench-surface">{workbench}</section>
        </main>
      </div>

      <DetailPanel config={detailView} onClose={() => setDetailView(null)} />
    </div>
  );
}
