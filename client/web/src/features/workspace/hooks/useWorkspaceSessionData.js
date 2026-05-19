import { useCallback, useEffect, useMemo, useRef, useState } from "react";

import {
  fetchSessionOverview,
  fetchSessionTranscript,
} from "../../../services/session-api.js";
import {
  fetchFinalReportStatus,
  fetchReportDetail,
} from "../../../services/report-api.js";
import {
  resolveMeetingWorkflowStatus,
  resolveWorkflowStatus,
} from "../../../app/workspace-model.js";
import {
  TRANSCRIPT_BATCH_SIZE,
  buildSessionViewState,
  debugWorkspace,
  shouldClearActionNotice,
} from "./useWorkspaceSessionData.helpers.js";
import useWorkspaceSessionActions from "./useWorkspaceSessionActions.js";
import useWorkspaceSessionPolling from "./useWorkspaceSessionPolling.js";

/**
 * 워크스페이스 세션 단위 데이터 로드와 polling, 재생성/회의록 액션을 담당한다.
 * 화면 컴포넌트는 이 hook이 만든 상태를 소비하고 렌더링에만 집중한다.
 */
export default function useWorkspaceSessionData({ onRefreshWorkspace, refreshToken, sessionId }) {
  const isMountedRef = useRef(true);
  const shouldSyncWorkspaceRef = useRef(false);
  const hasLoadedSessionRef = useRef(false);
  const previousSessionIdRef = useRef(sessionId);
  const latestSessionIdRef = useRef(sessionId);
  const loadRequestIdRef = useRef(0);
  const overviewRef = useRef(null);

  const [overview, setOverview] = useState(null);
  const [transcript, setTranscript] = useState(null);
  const [reportStatus, setReportStatus] = useState(null);
  const [latestReport, setLatestReport] = useState(null);
  const [reportDetail, setReportDetail] = useState(null);
  const [loading, setLoading] = useState(true);
  const [transcriptLoading, setTranscriptLoading] = useState(false);
  const [reportDetailLoading, setReportDetailLoading] = useState(false);
  const [error, setError] = useState(null);
  const [actionError, setActionError] = useState(null);
  const [actionNotice, setActionNotice] = useState(null);
  const [processingAction, setProcessingAction] = useState(false);

  const isStaleRequest = useCallback((requestedSessionId, requestId) => {
    return (
      !isMountedRef.current ||
      latestSessionIdRef.current !== requestedSessionId ||
      loadRequestIdRef.current !== requestId
    );
  }, []);

  const loadTranscriptProgressively = useCallback(
    async ({ requestId, requestedSessionId }) => {
      let afterSeqNum = null;
      let accumulatedItems = [];

      while (true) {
        const nextBatch = await fetchSessionTranscript({
          sessionId: requestedSessionId,
          limit: TRANSCRIPT_BATCH_SIZE,
          afterSeqNum,
        });

        if (isStaleRequest(requestedSessionId, requestId)) {
          return;
        }

        accumulatedItems = accumulatedItems.concat(nextBatch.items ?? []);
        setTranscript({
          ...nextBatch,
          items: accumulatedItems,
        });

        if (!nextBatch.has_more || nextBatch.next_after_seq_num == null) {
          return;
        }

        afterSeqNum = nextBatch.next_after_seq_num;
      }
    },
    [isStaleRequest],
  );

  const loadSessionData = useCallback(
    async ({
      background = false,
      includeOverview = true,
      includeTranscript = true,
      includeReportDetail = true,
    } = {}) => {
      debugWorkspace("load:start", {
        background,
        includeOverview,
        includeReportDetail,
        includeTranscript,
        sessionId,
      });

      if (!background) {
        setLoading(true);
        setError(null);
        setActionError(null);
      }

      const requestId = ++loadRequestIdRef.current;
      const requestedSessionId = sessionId;

      const nextReportStatusPromise = fetchFinalReportStatus({ sessionId });
      const nextOverviewPromise = includeOverview
        ? fetchSessionOverview({ sessionId })
        : Promise.resolve(overviewRef.current);

      const [nextReportStatus, nextOverview] = await Promise.all([
        nextReportStatusPromise,
        nextOverviewPromise,
      ]);

      if (isStaleRequest(requestedSessionId, requestId)) {
        return;
      }

      setOverview(nextOverview);
      setReportStatus(nextReportStatus);

      if (shouldClearActionNotice({ overview: nextOverview, reportStatus: nextReportStatus })) {
        setActionNotice(null);
      }

      hasLoadedSessionRef.current = true;

      if (!background) {
        setLoading(false);
      }

      if (includeTranscript) {
        setTranscriptLoading(true);
        void (background
          ? fetchSessionTranscript({ sessionId: requestedSessionId })
          : loadTranscriptProgressively({ requestId, requestedSessionId }))
          .then((nextTranscript) => {
            if (background && !isStaleRequest(requestedSessionId, requestId)) {
              setTranscript(nextTranscript);
            }
          })
          .catch((nextError) => {
            if (isStaleRequest(requestedSessionId, requestId)) {
              return;
            }
            debugWorkspace("load:transcript-error", {
              error: nextError instanceof Error ? nextError.message : String(nextError),
              sessionId: requestedSessionId,
            });
          })
          .finally(() => {
            if (isStaleRequest(requestedSessionId, requestId)) {
              return;
            }
            setTranscriptLoading(false);
          });
      } else {
        setTranscriptLoading(false);
      }

      if (
        includeReportDetail &&
        nextReportStatus.status === "completed" &&
        nextReportStatus.latest_report_id
      ) {
        setReportDetailLoading(true);
        void fetchReportDetail({
          sessionId,
          reportId: nextReportStatus.latest_report_id,
        })
          .then((nextReportDetail) => {
            if (isStaleRequest(requestedSessionId, requestId)) {
              return;
            }
            setLatestReport(nextReportDetail);
            setReportDetail(nextReportDetail);
          })
          .catch((nextError) => {
            if (isStaleRequest(requestedSessionId, requestId)) {
              return;
            }
            debugWorkspace("load:report-detail-error", {
              error: nextError instanceof Error ? nextError.message : String(nextError),
              reportId: nextReportStatus.latest_report_id,
              sessionId: requestedSessionId,
            });
          })
          .finally(() => {
            if (isStaleRequest(requestedSessionId, requestId)) {
              return;
            }
            setReportDetailLoading(false);
          });
      } else if (includeReportDetail) {
        setLatestReport(null);
        setReportDetail(null);
        setReportDetailLoading(false);
      } else if (!includeReportDetail) {
        setReportDetailLoading(false);
      }
    },
    [isStaleRequest, loadTranscriptProgressively, sessionId],
  );

  useEffect(() => {
    overviewRef.current = overview;
  }, [overview]);

  useEffect(() => {
    isMountedRef.current = true;
    return () => {
      isMountedRef.current = false;
    };
  }, []);

  useEffect(() => {
    latestSessionIdRef.current = sessionId;
  }, [sessionId]);

  useEffect(() => {
    let cancelled = false;
    const sameSession = previousSessionIdRef.current === sessionId;
    const shouldLoadInBackground = hasLoadedSessionRef.current && sameSession;
    previousSessionIdRef.current = sessionId;

    async function loadSession() {
      try {
        debugWorkspace("effect:load-session", {
          refreshToken,
          sameSession,
          sessionId,
          shouldLoadInBackground,
        });
        await loadSessionData({ background: shouldLoadInBackground });
      } catch (nextError) {
        if (cancelled || latestSessionIdRef.current !== sessionId) {
          return;
        }

        if (!shouldLoadInBackground) {
          setError(
            nextError instanceof Error
              ? nextError.message
              : "회의 화면을 불러오지 못했습니다.",
          );
          setLoading(false);
        }
      }
    }

    void loadSession();
    return () => {
      cancelled = true;
    };
  }, [loadSessionData, refreshToken, sessionId]);

  useEffect(() => {
    hasLoadedSessionRef.current = false;
    setActionNotice(null);
    setTranscript(null);
    setLatestReport(null);
    setReportDetail(null);
    setReportStatus(null);
    setTranscriptLoading(false);
    setReportDetailLoading(false);
  }, [sessionId]);

  const session = overview?.session ?? null;
  const reportWorkflow = useMemo(
    () => resolveWorkflowStatus(session, reportStatus),
    [reportStatus, session],
  );
  const workflow = useMemo(
    () => resolveMeetingWorkflowStatus(session, reportStatus),
    [reportStatus, session],
  );
  const sessionView = useMemo(
    () =>
      buildSessionViewState({
        latestReport,
        session,
        sessionId,
        workflow,
      }),
    [
      latestReport,
      session,
      sessionId,
      workflow.pipelineStage,
      workflow.status,
    ],
  );

  useWorkspaceSessionPolling({
    hasLoadedSessionRef,
    isLive: sessionView.isLive,
    loadSessionData,
    loading,
    onRefreshWorkspace,
    overview,
    reportStatus,
    reportWorkflow,
    session,
    shouldSyncWorkspaceRef,
  });

  const {
    handleGenerateReport,
    handlePrimaryAction,
    handleReportEdited,
  } = useWorkspaceSessionActions({
    latestReport,
    loadSessionData,
    onRefreshWorkspace,
    reportPipelineStage: reportWorkflow.pipelineStage,
    sessionId,
    setActionError,
    setActionNotice,
    setLatestReport,
    setOverview,
    setProcessingAction,
    setReportDetail,
    setReportStatus,
    shouldSyncWorkspaceRef,
  });

  return {
    actionError,
    actionNotice,
    canDownloadRecording: sessionView.canDownloadRecording,
    downloadHref: sessionView.downloadHref,
    error,
    handleGenerateReport,
    handlePrimaryAction,
    handleReportEdited,
    hidePreviousNote: sessionView.hidePreviousNote,
    loading,
    overview,
    processingAction,
    reportArtifactUrls: sessionView.reportArtifactUrls,
    reportDetailLoading,
    reportDetail,
    reportStatus,
    reportWorkflow,
    session,
    showTranscriptProgressHero: sessionView.showTranscriptProgressHero,
    transcript,
    transcriptLoading,
    visibleLatestReport: sessionView.visibleLatestReport,
    workflow,
  };
}
