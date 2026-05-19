/** WorkspaceTranscriptPanel의 순수 계산/문구 helper. */

export const BADGE_COPY = {
  context: { label: "CONTEXT", tone: "context" },
  decision: { label: "DECISION", tone: "decision" },
  action_item: { label: "ACTION ITEM", tone: "action" },
  question: { label: "QUESTION", tone: "question" },
  risk: { label: "RISK", tone: "risk" },
};

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

function formatTranscriptTime(startMs) {
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

export function canPlayTranscriptRow(row) {
  return Number.isFinite(row?.startMs) && Number.isFinite(row?.endMs) && row.endMs > row.startMs;
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
        speaker: item.speaker_label || "참석자",
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

export function buildEmptyState(workflow) {
  if (workflow.pipelineStage === "post_processing" && workflow.status === "failed") {
    return {
      tone: "failed",
      title: "노트 생성을 이어가지 못했습니다",
      progressLabel: "작업 멈춤",
      actionLabel: "노트 다시 만들기",
    };
  }

  if (workflow.pipelineStage === "note_correction" && workflow.status === "failed") {
    return {
      tone: "failed",
      title: "노트 보정이 멈췄습니다",
      progressLabel: "작업 멈춤",
      actionLabel: "노트 다시 만들기",
    };
  }

  if (workflow.pipelineStage === "report_generation" && workflow.status === "failed") {
    return {
      tone: "failed",
      title: "회의록 생성을 이어가지 못했습니다",
      progressLabel: "작업 멈춤",
      actionLabel: "회의록 다시 생성",
    };
  }

  if (workflow.pipelineStage === "recovery") {
    return {
      tone: "failed",
      title: "회의가 비정상 종료되었습니다",
      progressLabel: "복구 필요",
      actionLabel: "노트 만들기",
    };
  }

  if (workflow.pipelineStage === "post_processing") {
    if (workflow.status === "failed") {
      return {
        tone: "failed",
        title: "회의 정리에 실패했습니다",
        progressLabel: "정리 실패",
        actionLabel: "노트 다시 만들기",
      };
    }
    if (workflow.status === "processing") {
      return {
        tone: "processing",
        title: "회의를 정리하고 있습니다",
        progressLabel: "정리 중",
        actionLabel: null,
      };
    }
    return {
      tone: "pending",
      title: "회의 정리를 준비하고 있습니다",
      progressLabel: "정리 대기",
      actionLabel: null,
    };
  }

  if (workflow.pipelineStage === "note_correction") {
    if (workflow.status === "failed") {
      return {
        tone: "failed",
        title: "노트 보정에 실패했습니다",
        progressLabel: "보정 실패",
        actionLabel: "노트 다시 만들기",
      };
    }
    if (workflow.status === "processing") {
      return {
        tone: "processing",
        title: "노트를 다듬고 있습니다",
        progressLabel: "보정 중",
        actionLabel: null,
      };
    }
    return {
      tone: "pending",
      title: "노트 보정을 준비하고 있습니다",
      progressLabel: "보정 대기",
      actionLabel: null,
    };
  }

  if (workflow.pipelineStage === "report_generation") {
    if (workflow.status === "failed") {
      return {
        tone: "failed",
        title: "회의록 생성에 실패했습니다",
        progressLabel: "회의록 실패",
        actionLabel: "회의록 다시 생성",
      };
    }
    if (workflow.status === "processing") {
      return {
        tone: "processing",
        title: "회의록을 작성하고 있습니다",
        progressLabel: "회의록 생성 중",
        actionLabel: null,
      };
    }
    return {
      tone: "pending",
      title: "회의록 생성을 기다리고 있습니다",
      progressLabel: "회의록 대기",
      actionLabel: "회의록 생성",
    };
  }

  if (workflow.category === "running") {
    return {
      tone: "live",
      title: "회의가 진행 중입니다",
      progressLabel: "실시간 회의",
      actionLabel: null,
    };
  }

  return {
    tone: "default",
    title: "아직 표시할 회의 내용이 없습니다",
    progressLabel: "준비 중",
    actionLabel: null,
  };
}

export function resolveReportActionCopy(reportWorkflow, reportStatus) {
  const warningReason = String(reportStatus?.warning_reason ?? "").toLowerCase();
  if (warningReason === "report_generation_fallback") {
    return {
      actionLabel: "회의록 다시 만들기",
      description:
        reportStatus?.latest_job_error_message ||
        "PDF는 만들었지만 회의록 분석이 완료되지 않아 기본 회의록으로 생성했습니다.",
      tone: "warning",
      title: "기본 회의록으로 생성됐습니다",
    };
  }

  if (reportWorkflow?.pipelineStage !== "report_generation") {
    return null;
  }

  const errorMessage =
    reportStatus?.latest_job_error_message ||
    reportStatus?.warning_reason ||
    "회의록 생성 작업이 완료되지 않았습니다. 다시 생성해 보세요.";

  if (reportWorkflow.status === "failed") {
    return {
      actionLabel: "회의록 다시 생성",
      description: errorMessage,
      tone: "failed",
      title: "회의록 생성에 실패했습니다",
    };
  }

  if (reportWorkflow.status === "processing") {
    return {
      actionLabel: null,
      description: "완료되면 PDF 다운로드와 HTML 미리보기가 활성화됩니다.",
      tone: "processing",
      title: "회의록을 만드는 중입니다",
    };
  }

  if (reportWorkflow.status === "pending") {
    return {
      actionLabel: "회의록 생성",
      description: "정리된 노트를 바탕으로 PDF, HTML, Markdown 회의록을 만듭니다.",
      tone: "pending",
      title: "다운로드할 회의록을 만들 수 있습니다",
    };
  }

  return null;
}
