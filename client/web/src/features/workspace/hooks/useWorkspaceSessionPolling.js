import { useEffect } from "react";

import { buildPollingPlan } from "./useWorkspaceSessionData.helpers.js";

export default function useWorkspaceSessionPolling({
  hasLoadedSessionRef,
  isLive,
  loadSessionData,
  loading,
  onRefreshWorkspace,
  overview,
  reportStatus,
  reportWorkflow,
  session,
  shouldSyncWorkspaceRef,
}) {
  useEffect(() => {
    if (loading || !hasLoadedSessionRef.current || !session || reportStatus == null) {
      return undefined;
    }

    const pollingPlan = buildPollingPlan({
      isLive,
      overview,
      reportStatus,
      workflow: reportWorkflow,
    });

    if (pollingPlan) {
      shouldSyncWorkspaceRef.current = true;
      const timerId = window.setTimeout(() => {
        void loadSessionData({
          background: true,
          ...pollingPlan.loadOptions,
        }).catch(() => {});
      }, pollingPlan.intervalMs);

      return () => {
        window.clearTimeout(timerId);
      };
    }

    if (shouldSyncWorkspaceRef.current && ["completed", "failed"].includes(reportWorkflow.status)) {
      shouldSyncWorkspaceRef.current = false;
      void onRefreshWorkspace({ background: true, syncSession: false });
    }

    return undefined;
  }, [
    hasLoadedSessionRef,
    isLive,
    loadSessionData,
    loading,
    onRefreshWorkspace,
    overview,
    reportStatus,
    reportWorkflow,
    session,
    shouldSyncWorkspaceRef,
  ]);
}
