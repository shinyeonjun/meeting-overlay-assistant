/**
 * 워크스페이스 회의 화면의 순수 계산 로직(포맷, 발화 행, 안내 문구, 폴링 계획).
 * React나 DOM 상태를 쓰지 않으므로 node:test로 바로 검증할 수 있다.
 */

export const BADGE_COPY = {
  context: { label: "CONTEXT", tone: "context" },
  decision: { label: "DECISION", tone: "decision" },
  action_item: { label: "ACTION ITEM", tone: "action" },
  question: { label: "QUESTION", tone: "question" },
  risk: { label: "RISK", tone: "risk" },
};

export const POST_PROCESSING_POLL_INTERVAL_MS = 5000;
export const REPORT_GENERATION_POLL_INTERVAL_MS = 6000;

export function formatMeetingDate(value) {
  if (!value) {
    return "-";
  }

  try {
    return new Date(value).toLocaleString("ko-KR", {
      year: "numeric",
      month: "long",
      day: "numeric",
      weekday: "short",
    });
  } catch {
    return value;
  }
}

export function formatTranscriptTime(startMs) {
  const totalSeconds = Math.max(0, Math.floor(Number(startMs || 0) / 1000));
  const minutes = Math.floor(totalSeconds / 60);
  const seconds = totalSeconds % 60;
  const hours = Math.floor(minutes / 60);
  const minuteValue = minutes % 60;

  if (hours > 0) {
    return `${String(hours).padStart(2, "0")}:${String(minuteValue).padStart(2, "0")}:${String(seconds).padStart(2, "0")}`;
  }
  return `${String(minuteValue).padStart(2, "0")}:${String(seconds).padStart(2, "0")}`;
}

export function formatAudioClock(totalSeconds) {
  const safeSeconds = Number.isFinite(totalSeconds) ? Math.max(0, Math.floor(totalSeconds)) : 0;
  const hours = Math.floor(safeSeconds / 3600);
  const minutes = Math.floor((safeSeconds % 3600) / 60);
  const seconds = safeSeconds % 60;

  if (hours > 0) {
    return `${String(hours).padStart(2, "0")}:${String(minutes).padStart(2, "0")}:${String(seconds).padStart(2, "0")}`;
  }
  return `${String(minutes).padStart(2, "0")}:${String(seconds).padStart(2, "0")}`;
}

export function formatModeLabel(mode) {
  switch (String(mode ?? "").toLowerCase()) {
    case "strategy":
      return "전략 회의";
    case "review":
      return "리뷰 회의";
    case "daily":
      return "데일리";
    default:
      return "일반 회의";
  }
}

export function formatEventState(state) {
  switch (String(state ?? "").toLowerCase()) {
    case "open":
    case "active":
      return "진행 중";
    case "resolved":
      return "해결";
    case "closed":
      return "종료";
    case "completed":
      return "완료";
    case "pending":
      return "대기";
    default:
      return state || "확인 필요";
  }
}

/** 화자 목록 응답을 {speaker_label: 표시 이름}으로 바꾼다. */
export function buildSpeakerNameMap(speakers) {
  const names = new Map();
  for (const item of speakers?.items ?? []) {
    if (item?.speaker_label && item.display_name) {
      names.set(item.speaker_label, item.display_name);
    }
  }
  return names;
}

/**
 * 이벤트의 화자 라벨을 화면에 보여 줄 이름으로 바꾼다. 라벨이 없거나 모르는 라벨이면 null이다.
 * 발화는 서버가 speaker_name을 함께 주므로 이 함수를 쓰지 않는다.
 */
export function resolveSpeakerName(speakerLabel, speakerNames) {
  const label = String(speakerLabel ?? "").trim();
  return (label && speakerNames?.get(label)) || null;
}

/** 화자 이름 편집 줄을 보여 줄지 정한다. 정리 중이거나 진행 중인 회의는 라벨이 바뀔 수 있어 숨긴다. */
export function canEditSpeakerNames({ isLive, speakers, workflow }) {
  if (isLive || !speakers?.items?.length) {
    return false;
  }
  const isPostProcessing =
    workflow?.pipelineStage === "post_processing" &&
    ["pending", "processing"].includes(workflow?.status);
  return !isPostProcessing;
}

export function buildTranscriptRows({ overview, reportDetail, transcriptItems }) {
  const speakerTranscript =
    transcriptItems?.length > 0 ? transcriptItems : (reportDetail?.speaker_transcript ?? []);
  const speakerEvents = reportDetail?.speaker_events ?? [];

  if (speakerTranscript.length > 0) {
    const queueBySpeaker = new Map();
    for (const event of speakerEvents) {
      const key = event.speaker_label || "__default";
      const queue = queueBySpeaker.get(key) ?? [];
      queue.push(event);
      queueBySpeaker.set(key, queue);
    }

    return speakerTranscript.map((item, index) => {
      const key = item.speaker_label || "__default";
      const queue = queueBySpeaker.get(key) ?? [];
      const badge = queue.length > 0 ? queue.shift() : null;
      return {
        id: `${item.speaker_label}-${item.start_ms}-${index}`,
        speaker: item.speaker_name || item.speaker_label || "참석자",
        time: formatTranscriptTime(item.start_ms),
        text: item.text,
        isDraft: item.transcript_source === "post_processing_draft",
        badge,
        startMs: Number(item.start_ms ?? 0),
        endMs: Number(item.end_ms ?? 0),
      };
    });
  }

  const fallbackEvents = [
    ...(overview?.decisions ?? []).map((item) => ({ ...item, event_type: "decision" })),
    ...(overview?.action_items ?? []).map((item) => ({ ...item, event_type: "action_item" })),
    ...(overview?.questions ?? []).map((item) => ({ ...item, event_type: "question" })),
    ...(overview?.risks ?? []).map((item) => ({ ...item, event_type: "risk" })),
  ];

  return fallbackEvents.slice(0, 8).map((item, index) => ({
    id: item.id,
    speaker: item.speaker_label || "회의 메모",
    time: formatTranscriptTime(index * 90 * 1000),
    text: item.title,
    badge: {
      speaker_label: item.speaker_label,
      event_type: item.event_type,
      title: item.title,
      state: item.state,
    },
    startMs: null,
    endMs: null,
  }));
}

export function canPlayTranscriptRow(row) {
  return Number.isFinite(row?.startMs) && Number.isFinite(row?.endMs) && row.endMs > row.startMs;
}

export function waitForAudioMetadata(audio) {
  if (audio.readyState >= 1) {
    return Promise.resolve();
  }

  return new Promise((resolve, reject) => {
    function handleLoaded() {
      cleanup();
      resolve();
    }

    function handleError() {
      cleanup();
      reject(new Error("녹음 파일 메타데이터를 불러오지 못했습니다."));
    }

    function cleanup() {
      audio.removeEventListener("loadedmetadata", handleLoaded);
      audio.removeEventListener("error", handleError);
    }

    audio.addEventListener("loadedmetadata", handleLoaded);
    audio.addEventListener("error", handleError);
  });
}

export function buildAssistantMessages({ actionItems, currentTopic, decisions }) {
  const assistantIntro = {
    role: "assistant",
    text: "회의 내용을 기준으로 궁금한 점을 바로 물어볼 수 있습니다.",
  };

  if (actionItems.length > 0) {
    return [
      assistantIntro,
      {
        role: "user",
        text: "지금 가장 먼저 챙겨야 할 액션이 뭐야?",
      },
      {
        role: "assistant",
        text: `${actionItems[0].title}${actionItems[0].speaker_label ? `, 담당은 ${actionItems[0].speaker_label}` : ""}`,
        linkText: "근거 보기",
      },
    ];
  }

  if (decisions.length > 0) {
    return [
      assistantIntro,
      {
        role: "user",
        text: "이번 회의에서 확정된 핵심 결정이 뭐야?",
      },
      {
        role: "assistant",
        text: decisions[0].title,
        linkText: "회의 근거 보기",
      },
    ];
  }

  return [
    assistantIntro,
    {
      role: "assistant",
      text: currentTopic || "아직 정리된 회의 요약이 없습니다.",
    },
  ];
}

export function buildEmptyState(workflow) {
  if (workflow.pipelineStage === "recovery") {
    return {
      tone: "failed",
      title: "회의가 비정상 종료되었습니다",
      progressLabel: "복구 필요",
      actionLabel: "노트 만들기",
      actionKind: "reprocess",
    };
  }

  if (workflow.pipelineStage === "post_processing") {
    if (workflow.status === "failed") {
      return {
        tone: "failed",
        title: "회의 정리에 실패했습니다",
        progressLabel: "정리 실패",
        actionLabel: "노트 다시 만들기",
        actionKind: "reprocess",
      };
    }
    if (workflow.status === "processing") {
      return {
        tone: "processing",
        title: "회의를 정리하고 있습니다",
        progressLabel: "정리 중",
        actionLabel: null,
        actionKind: null,
      };
    }
    return {
      tone: "pending",
      title: "회의 정리를 준비하고 있습니다",
      progressLabel: "정리 대기",
      actionLabel: null,
      actionKind: null,
    };
  }

  if (workflow.pipelineStage === "note_correction") {
    if (workflow.status === "failed") {
      return {
        tone: "failed",
        title: "노트 보정이 실패했습니다",
        progressLabel: "노트 보정 실패",
        actionLabel: "노트 다시 만들기",
        actionKind: "reprocess",
      };
    }
    if (workflow.status === "processing") {
      return {
        tone: "processing",
        title: "노트를 보정하고 있습니다",
        progressLabel: "노트 보정 중",
        actionLabel: null,
        actionKind: null,
      };
    }
    return {
      tone: "pending",
      title: "노트 보정을 준비하고 있습니다",
      progressLabel: "노트 보정 대기",
      actionLabel: null,
      actionKind: null,
    };
  }

  if (workflow.pipelineStage === "report_generation") {
    if (workflow.status === "failed") {
      return {
        tone: "failed",
        title: "리포트 생성에 실패했습니다",
        progressLabel: "리포트 실패",
        actionLabel: "리포트 다시 생성",
        actionKind: "report",
      };
    }
    if (workflow.status === "processing") {
      return {
        tone: "processing",
        title: "리포트를 작성하고 있습니다",
        progressLabel: "리포트 생성 중",
        actionLabel: null,
        actionKind: null,
      };
    }
    return {
      tone: "pending",
      title: "리포트 생성을 기다리고 있습니다",
      progressLabel: "리포트 대기",
      actionLabel: "리포트 생성",
      actionKind: "report",
    };
  }

  if (workflow.category === "running") {
    return {
      tone: "live",
      title: "회의가 진행 중입니다",
      progressLabel: "실시간 회의",
      actionLabel: null,
      actionKind: null,
    };
  }

  return {
    tone: "default",
    title: "아직 표시할 transcript가 없습니다",
    progressLabel: "준비 중",
    actionLabel: null,
    actionKind: null,
  };
}

export function buildPollingPlan({ isLive, reportStatus, workflow }) {
  if (isLive) {
    return null;
  }

  const latestJobStatus = String(reportStatus?.latest_job_status ?? "").toLowerCase();
  const isPostProcessingActive =
    workflow.pipelineStage === "post_processing" &&
    ["pending", "processing"].includes(workflow.status);
  if (isPostProcessingActive) {
    return {
      intervalMs: POST_PROCESSING_POLL_INTERVAL_MS,
      phase: "post_processing",
      loadOptions: {
        includeOverview: false,
        includeTranscript: true,
        includeReportDetail: false,
      },
    };
  }

  const isNoteCorrectionActive =
    workflow.pipelineStage === "note_correction" &&
    ["pending", "processing"].includes(workflow.status);
  if (isNoteCorrectionActive) {
    return {
      intervalMs: REPORT_GENERATION_POLL_INTERVAL_MS,
      phase: "note_correction",
      loadOptions: {
        includeOverview: false,
        includeTranscript: true,
        includeReportDetail: false,
      },
    };
  }

  const isReportGenerationActive =
    workflow.pipelineStage === "report_generation" &&
    ["pending", "processing"].includes(latestJobStatus);
  if (isReportGenerationActive) {
    return {
      intervalMs: REPORT_GENERATION_POLL_INTERVAL_MS,
      phase: "report_generation",
      loadOptions: {
        includeOverview: false,
        includeTranscript: false,
        includeReportDetail: true,
      },
    };
  }

  return null;
}

/** 세션에 녹음 파일이 연결돼 있으면 재생기와 원본 다운로드를 노출한다. */
export function hasRecordingAvailable(session) {
  return Boolean(session?.recording_available || session?.recording_artifact_id);
}

/** 완료된 리포트의 상세를 다시 가져와야 하는지 판단한다. */
export function shouldFetchLatestReport(reportStatus, includeReportDetail) {
  return Boolean(
    includeReportDetail && reportStatus.status === "completed" && reportStatus.latest_report_id,
  );
}

/** 요청 시점과 현재 세션/요청 번호가 달라진 늦은 응답인지 판단한다. */
export function isStaleWorkspaceResponse({
  latestRequestId,
  latestSessionId,
  requestId,
  requestedSessionId,
}) {
  return latestSessionId !== requestedSessionId || latestRequestId !== requestId;
}

/** 불러온 상태가 완료 또는 후처리 종료이면 이전 액션 안내를 지워도 되는지 판단한다. */
export function shouldClearActionNoticeAfterLoad(reportStatus, overview) {
  const postProcessingStatus = overview?.session?.post_processing_status;
  return (
    reportStatus?.status === "completed" ||
    Boolean(postProcessingStatus && !["queued", "processing"].includes(postProcessingStatus))
  );
}
