import { useCallback, useEffect, useMemo, useRef, useState } from "react";

import { getWorkspaceLoadOptions } from "../../../app/workspace-modes.js";
import {
  groupSessionsByOperationalState,
  resolveWorkflowStatus,
  sortSessionsByStartedAt,
} from "../../../app/workspace-model.js";
import { fetchWorkspaceOverview } from "../../../services/workspace-api.js";

const WORKSPACE_BACKGROUND_POLL_INTERVAL_MS = 5000;
const STARTUP_RECOVERY_REFRESH_DELAY_MS = 3000;

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

async function loadWorkspaceData(mode) {
  const overview = await fetchWorkspaceOverview(getWorkspaceLoadOptions(mode));
  return {
    ...overview,
    reportStatuses: overview.report_statuses ?? {},
  };
}

function hasActiveWorkspaceJobs(sessions, reportStatuses) {
  return (sessions ?? []).some((session) => {
    const reportStatus = reportStatuses?.[session.id];
    const workflow = resolveWorkflowStatus(session, reportStatus);
    const latestJobStatus = String(reportStatus?.latest_job_status ?? "").toLowerCase();
    return (
      workflow.category === "processing" ||
      workflow.status === "processing" ||
      latestJobStatus === "pending" ||
      latestJobStatus === "processing"
    );
  });
}

function hasRunningWorkspaceSession(workspaceData) {
  return (workspaceData?.sessions ?? []).some(
    (session) => String(session?.status ?? "").toLowerCase() === "running",
  );
}

function useWorkspaceBoot({ activeMode, setError, setLoading, setWorkspaceData }) {
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
  }, [activeMode, setError, setLoading, setWorkspaceData]);
}

function useStartupRecoveryRefresh({
  activeMode,
  loading,
  setWorkspaceData,
  setWorkspaceRefreshToken,
  startupRecoveryRefreshScheduledRef,
  workspaceData,
}) {
  useEffect(() => {
    if (
      loading ||
      workspaceData == null ||
      startupRecoveryRefreshScheduledRef.current ||
      !hasRunningWorkspaceSession(workspaceData)
    ) {
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
        // 시작 직후 복구 상태 동기화는 다음 polling 주기에 다시 시도된다.
      }
    }, STARTUP_RECOVERY_REFRESH_DELAY_MS);

    return () => {
      cancelled = true;
      window.clearTimeout(timerId);
    };
  }, [
    activeMode,
    loading,
    setWorkspaceData,
    setWorkspaceRefreshToken,
    startupRecoveryRefreshScheduledRef,
    workspaceData,
  ]);
}

function useActiveWorkspacePolling({
  activeMode,
  loading,
  reportStatuses,
  sessions,
  setWorkspaceData,
  workspaceData,
}) {
  useEffect(() => {
    if (loading || workspaceData == null || !hasActiveWorkspaceJobs(sessions, reportStatuses)) {
      return undefined;
    }

    let cancelled = false;
    const timerId = window.setTimeout(async () => {
      try {
        const nextData = await loadWorkspaceData(activeMode);
        if (!cancelled) {
          setWorkspaceData(nextData);
        }
      } catch {
        // 백그라운드 갱신 실패는 다음 polling 주기에 다시 시도된다.
      }
    }, WORKSPACE_BACKGROUND_POLL_INTERVAL_MS);

    return () => {
      cancelled = true;
      window.clearTimeout(timerId);
    };
  }, [activeMode, loading, reportStatuses, sessions, setWorkspaceData, workspaceData]);
}

export default function useWorkspaceShellData(activeMode) {
  const startupRecoveryRefreshScheduledRef = useRef(false);
  const [workspaceData, setWorkspaceData] = useState(null);
  const [selectedSessionId, setSelectedSessionId] = useState();
  const [workspaceRefreshToken, setWorkspaceRefreshToken] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useWorkspaceBoot({
    activeMode,
    setError,
    setLoading,
    setWorkspaceData,
  });

  useStartupRecoveryRefresh({
    activeMode,
    loading,
    setWorkspaceData,
    setWorkspaceRefreshToken,
    startupRecoveryRefreshScheduledRef,
    workspaceData,
  });

  const sessions = useMemo(
    () => sortSessionsByStartedAt(workspaceData?.sessions ?? []),
    [workspaceData],
  );
  const reportStatuses = workspaceData?.reportStatuses ?? {};
  const grouped = useMemo(
    () => groupSessionsByOperationalState(sessions, reportStatuses),
    [sessions, reportStatuses],
  );

  useActiveWorkspacePolling({
    activeMode,
    loading,
    reportStatuses,
    sessions,
    setWorkspaceData,
    workspaceData,
  });

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

  const refreshWorkspace = useCallback(async (options = {}) => {
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
      setError(nextError instanceof Error ? nextError.message : "새로고침에 실패했습니다.");
    } finally {
      if (!background) {
        setLoading(false);
      }
    }
  }, [activeMode]);

  return {
    error,
    grouped,
    loading,
    refreshWorkspace,
    reportStatuses,
    selectedSessionId,
    sessions,
    setSelectedSessionId,
    setWorkspaceData,
    workspaceData,
    workspaceRefreshToken,
  };
}
