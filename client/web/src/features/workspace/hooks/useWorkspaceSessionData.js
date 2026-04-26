import { useCallback, useEffect, useMemo, useRef, useState } from "react";

import {
  fetchSessionOverview,
  fetchSessionTranscript,
  reprocessSession,
} from "../../../services/session-api.js";
import {
  enqueueReportGenerationJob,
  fetchFinalReportStatus,
  fetchReportDetail,
} from "../../../services/report-api.js";
import { buildApiUrl } from "../../../config/runtime.js";
import {
  isLiveSession,
  resolveMeetingWorkflowStatus,
  resolveWorkflowStatus,
} from "../../../app/workspace-model.js";

const POST_PROCESSING_POLL_INTERVAL_MS = 5000;
const REPORT_GENERATION_POLL_INTERVAL_MS = 6000;
const TRANSCRIPT_BATCH_SIZE = 48;
const WORKSPACE_DEBUG = import.meta.env.DEV;

function debugWorkspace(event, payload = {}) {
  if (!WORKSPACE_DEBUG) {
    return;
  }
  console.debug("[CAPS][workspace]", event, payload);
}

function isPostProcessingActive(status) {
  const normalized = String(status ?? "").toLowerCase();
  return (
    normalized === "queued" ||
    normalized === "processing" ||
    normalized.startsWith("processing_")
  );
}

function buildPollingPlan({ isLive, reportStatus, workflow }) {
  if (isLive) {
    return null;
  }

  const latestJobStatus = String(reportStatus?.latest_job_status ?? "").toLowerCase();
  if (
    workflow.pipelineStage === "post_processing" &&
    ["pending", "processing"].includes(workflow.status)
  ) {
    return {
      intervalMs: POST_PROCESSING_POLL_INTERVAL_MS,
      loadOptions: {
        includeOverview: false,
        includeTranscript: true,
        includeReportDetail: false,
      },
    };
  }

  if (
    workflow.pipelineStage === "note_correction" &&
    ["pending", "processing"].includes(workflow.status)
  ) {
    return {
      intervalMs: REPORT_GENERATION_POLL_INTERVAL_MS,
      loadOptions: {
        includeOverview: true,
        includeTranscript: true,
        includeReportDetail: false,
      },
    };
  }

  if (
    workflow.pipelineStage === "report_generation" &&
    (["pending", "processing"].includes(workflow.status) ||
      ["pending", "processing"].includes(latestJobStatus))
  ) {
    return {
      intervalMs: REPORT_GENERATION_POLL_INTERVAL_MS,
      loadOptions: {
        includeOverview: true,
        includeTranscript: false,
        includeReportDetail: true,
      },
    };
  }

  return null;
}

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
  const transcriptRef = useRef(null);

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

      if (
        nextReportStatus?.status === "completed" ||
        (nextOverview?.session?.post_processing_status &&
          !isPostProcessingActive(nextOverview.session.post_processing_status))
      ) {
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
    transcriptRef.current = transcript;
  }, [transcript]);

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
  const isLive = isLiveSession(session?.status);
  const canDownloadRecording = Boolean(
    session?.recording_available || session?.recording_artifact_id,
  );
  const downloadHref = canDownloadRecording
    ? buildApiUrl(`/api/v1/sessions/${sessionId}/recording?download=true`)
    : null;
  const hidePreviousNote =
    ["post_processing", "note_correction"].includes(workflow.pipelineStage) &&
    ["pending", "processing"].includes(workflow.status);
  const visibleLatestReport = hidePreviousNote ? null : latestReport;
  const showTranscriptProgressHero =
    ["post_processing", "note_correction"].includes(workflow.pipelineStage) &&
    ["pending", "processing"].includes(workflow.status);

  useEffect(() => {
    if (loading || !hasLoadedSessionRef.current || !session || reportStatus == null) {
      return undefined;
    }

    const pollingPlan = buildPollingPlan({ isLive, reportStatus, workflow: reportWorkflow });

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
    isLive,
    loadSessionData,
    loading,
    onRefreshWorkspace,
    reportStatus,
    session,
    reportWorkflow.pipelineStage,
    reportWorkflow.status,
  ]);

  const handleGenerateReport = useCallback(async () => {
    try {
      setProcessingAction(true);
      setActionError(null);
      const job = await enqueueReportGenerationJob({ sessionId });
      shouldSyncWorkspaceRef.current = true;
      setReportStatus((current) => ({
        ...(current ?? {}),
        session_id: sessionId,
        status: "processing",
        pipeline_stage: "report_generation",
        latest_job_status: job.status,
        latest_job_error_message: job.error_message ?? null,
      }));

      await loadSessionData({
        background: true,
        includeOverview: false,
        includeTranscript: false,
        includeReportDetail: false,
      });
      await onRefreshWorkspace({ background: true, syncSession: false });
    } catch (nextError) {
      setActionError(
        nextError instanceof Error
          ? nextError.message
          : "회의록 생성 요청이 실패했습니다.",
      );
    } finally {
      setProcessingAction(false);
    }
  }, [loadSessionData, onRefreshWorkspace, sessionId]);

  const handleReprocessNote = useCallback(async () => {
    try {
      setProcessingAction(true);
      setActionError(null);
      const nextSession = await reprocessSession({ sessionId });
      shouldSyncWorkspaceRef.current = true;
      setOverview((current) => ({
        ...(current ?? {}),
        session: nextSession,
      }));
      setReportStatus((current) => ({
        ...(current ?? {}),
        session_id: sessionId,
        status: "pending",
        pipeline_stage: "post_processing",
        post_processing_status: nextSession.post_processing_status ?? "queued",
        latest_job_status: null,
        latest_job_error_message: null,
      }));
      setActionNotice("재생성을 시작했습니다. 새 초안이 준비되는 대로 아래에 표시합니다.");
      setLatestReport(null);
      setReportDetail(null);
      await loadSessionData({
        background: true,
        includeOverview: false,
        includeTranscript: false,
        includeReportDetail: false,
      });
      await onRefreshWorkspace({ background: true, syncSession: false });
    } catch (nextError) {
      setActionError(
        nextError instanceof Error
          ? nextError.message
          : "노트 생성 요청을 처리하지 못했습니다.",
      );
    } finally {
      setProcessingAction(false);
    }
  }, [loadSessionData, onRefreshWorkspace, sessionId]);

  const handlePrimaryAction = useCallback(async () => {
    if (reportWorkflow.pipelineStage === "report_generation") {
      await handleGenerateReport();
      return;
    }
    await handleReprocessNote();
  }, [handleGenerateReport, handleReprocessNote, reportWorkflow.pipelineStage]);

  return {
    actionError,
    actionNotice,
    canDownloadRecording,
    downloadHref,
    error,
    handlePrimaryAction,
    hidePreviousNote,
    loading,
    overview,
    processingAction,
    reportDetailLoading,
    reportDetail,
    reportStatus,
    reportWorkflow,
    session,
    showTranscriptProgressHero,
    transcript,
    transcriptLoading,
    visibleLatestReport,
    workflow,
  };
}
