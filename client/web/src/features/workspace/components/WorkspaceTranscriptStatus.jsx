import React from "react";
import { Loader } from "lucide-react";

const STAGE_COPY = {
  post_processing: {
    processingTitle: "새 노트를 만드는 중입니다",
    pendingTitle: "노트 생성을 준비하고 있습니다",
    description: "분석이 끝나는 대로 아래 회의 내용이 순서대로 채워집니다.",
  },
  note_correction: {
    processingTitle: "노트를 다듬는 중입니다",
    pendingTitle: "노트 보정을 준비하고 있습니다",
    description: "먼저 정리한 초안 내용을 바탕으로 문장을 더 읽기 좋게 다듬고 있습니다.",
  },
  report_generation: {
    processingTitle: "회의록을 만드는 중입니다",
    pendingTitle: "회의록을 준비하고 있습니다",
    description: "노트가 정리되면 회의 요약과 후속 조치를 이어서 만듭니다.",
  },
  recovery: {
    processingTitle: "중단된 작업을 복구하는 중입니다",
    pendingTitle: "복구를 준비하고 있습니다",
    description: "이전 작업 상태를 확인한 뒤 이어서 정리합니다.",
  },
};

function resolveStageCopy(workflow, actionNotice) {
  if (workflow?.category === "failed" && workflow?.pipelineStage === "post_processing") {
    return {
      title: actionNotice || "노트 생성을 이어가지 못했습니다",
      description:
        "후처리 워커가 멈춘 상태일 수 있습니다. 워커를 다시 시작한 뒤 노트를 다시 정리하세요.",
    };
  }

  if (workflow?.category === "failed" && workflow?.pipelineStage === "note_correction") {
    return {
      title: actionNotice || "노트 보정이 멈췄습니다",
      description:
        "note-correction 워커가 멈춘 상태일 수 있습니다. 워커를 다시 시작한 뒤 노트를 다시 정리하세요.",
    };
  }

  if (workflow?.category === "failed" && workflow?.pipelineStage === "report_generation") {
    return {
      title: actionNotice || "회의록 생성을 이어가지 못했습니다",
      description:
        "회의록 워커가 멈춘 상태일 수 있습니다. 워커를 다시 시작한 뒤 회의록을 다시 생성하세요.",
    };
  }

  const stageCopy = STAGE_COPY[workflow?.pipelineStage] ?? STAGE_COPY.post_processing;
  const title =
    actionNotice ||
    (workflow?.status === "processing" ? stageCopy.processingTitle : stageCopy.pendingTitle);

  return {
    title,
    description: actionNotice
      ? "초안이 준비되는 순서대로 아래 회의 내용에 바로 표시됩니다."
      : stageCopy.description,
  };
}

/**
 * 노트 생성/재생성 중 상태를 한 번만 설명하는 카드다.
 * 초안이 생기기 전에는 hero로, 초안이 생긴 뒤에는 compact 배너로 줄어든다.
 */
export default function WorkspaceTranscriptStatus({
  actionNotice,
  compact = false,
  draftCount = 0,
  workflow,
}) {
  const { title, description } = resolveStageCopy(workflow, actionNotice);
  const countLabel = draftCount > 0 ? `초안 ${draftCount}줄` : null;
  const phaseLabel =
    draftCount > 0 ? "초안 작성 중" : workflow?.status === "processing" ? "정리 중" : "대기 중";

  return (
    <div className={`caps-transcript-status ${compact ? "compact" : "hero"}`}>
      <div className="caps-transcript-status-card">
        <div className="caps-transcript-status-head">
          <span className="caps-transcript-empty-pill processing">
            <Loader size={13} className="spinner" />
            {phaseLabel}
          </span>
          {countLabel ? <span className="caps-transcript-status-count">{countLabel}</span> : null}
        </div>

        <div className="caps-transcript-status-copy">
          <h3>{title}</h3>
          <p>{description}</p>
        </div>

        {!compact ? <div className="caps-transcript-status-bar" aria-hidden="true" /> : null}
      </div>
    </div>
  );
}
