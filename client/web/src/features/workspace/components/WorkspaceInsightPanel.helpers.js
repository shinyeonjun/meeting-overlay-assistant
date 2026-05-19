export function formatTimeRange(startMs, endMs) {
  const formatMs = (value) => {
    const totalSeconds = Math.max(Math.floor((value ?? 0) / 1000), 0);
    const minutes = Math.floor(totalSeconds / 60);
    const seconds = totalSeconds % 60;
    return `${String(minutes).padStart(2, "0")}:${String(seconds).padStart(2, "0")}`;
  };

  return `${formatMs(startMs)} - ${formatMs(endMs)}`;
}

export function normalizeInsightStatus(overview) {
  const status = String(overview?.workspace_summary_status?.status ?? "").toLowerCase();
  if (status) {
    return status;
  }
  return overview?.workspace_summary ? "completed" : "pending";
}

export function buildFallbackSummary(overview, session) {
  const questions = [...(overview?.questions ?? []), ...(overview?.risks ?? [])]
    .slice(0, 2)
    .map((item) => item.title);

  return {
    headline: overview?.current_topic || session?.title || "회의 요약이 아직 없습니다.",
    summary: overview?.current_topic
      ? [`이번 회의는 ${overview.current_topic} 중심으로 정리되었습니다.`]
      : ["아직 표시할 노트 인사이트가 없습니다."],
    topics: overview?.current_topic
      ? [
          {
            title: overview.current_topic,
            summary: `${overview.current_topic} 관련 논의가 있었습니다.`,
            start_ms: 0,
            end_ms: 0,
          },
        ]
      : [],
    decisions: (overview?.decisions ?? []).slice(0, 3).map((item) => item.title),
    next_actions: (overview?.action_items ?? []).slice(0, 3).map((item) => ({
      title: item.title,
      owner: item.speaker_label || null,
      due_date: null,
    })),
    open_questions: questions,
    changed_since_last_meeting: [],
    evidence: [],
  };
}

export function buildSummaryModel(overview, session) {
  const summary = overview?.workspace_summary;
  if (summary) {
    return {
      headline: summary.headline,
      summary: summary.summary ?? [],
      topics: summary.topics ?? [],
      decisions: summary.decisions ?? [],
      next_actions: summary.next_actions ?? [],
      open_questions: summary.open_questions ?? [],
      changed_since_last_meeting: summary.changed_since_last_meeting ?? [],
      evidence: summary.evidence ?? [],
    };
  }
  return buildFallbackSummary(overview, session);
}

export function buildStatusCopy({ actionNotice, hidePreviousNote, insightStatus, reportStatus }) {
  const warningReason = String(reportStatus?.warning_reason ?? "").toLowerCase();
  if (hidePreviousNote) {
    if (warningReason === "post_processing_stalled") {
      return {
        title: "노트 생성이 멈춘 상태입니다.",
        description: "후처리 워커를 확인한 뒤 노트를 다시 정리하세요.",
      };
    }
    if (warningReason === "note_correction_stalled") {
      return {
        title: "노트 정리가 멈춘 상태입니다.",
        description: "노트 보정 워커를 확인한 뒤 노트를 다시 정리하세요.",
      };
    }
    return {
      title: actionNotice || "노트를 정리하는 중입니다.",
      description: "전사와 보정이 끝나면 노트가 먼저 표시됩니다.",
    };
  }

  if (insightStatus === "processing" || insightStatus === "pending") {
    return {
      title: "노트 인사이트를 분석하는 중입니다.",
      description: "노트는 바로 확인할 수 있고, 분석 결과는 완료되는 즉시 이 패널에 표시됩니다.",
    };
  }

  if (insightStatus === "failed") {
    return {
      title: "노트 인사이트 분석에 실패했습니다.",
      description: "노트 본문은 사용할 수 있습니다. 필요하면 노트를 다시 정리해 분석을 재시도하세요.",
    };
  }

  if (insightStatus === "disabled") {
    return {
      title: "노트 인사이트 분석이 꺼져 있습니다.",
      description: "분석 기능을 켜면 요약, 결정 사항, 다음 할 일을 자동으로 정리합니다.",
    };
  }

  if (insightStatus === "not_ready") {
    return {
      title: "노트가 준비되면 인사이트를 분석합니다.",
      description: "회의 종료 후 전사와 노트 정리가 끝나면 분석이 자동으로 시작됩니다.",
    };
  }

  return null;
}
