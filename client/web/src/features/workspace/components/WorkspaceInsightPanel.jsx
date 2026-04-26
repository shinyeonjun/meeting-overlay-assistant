/** 오른쪽 요약 패널과 AI 보조 영역을 렌더링한다. */
import React from "react";
import { AlertTriangle, FileText, SendHorizontal, Sparkles } from "lucide-react";

import { getMeetingStatusLabel, getMeetingStatusTone } from "../../../app/workspace-model.js";

function formatEventState(state) {
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

function formatTimeRange(startMs, endMs) {
  const formatMs = (value) => {
    const totalSeconds = Math.max(Math.floor((value ?? 0) / 1000), 0);
    const minutes = Math.floor(totalSeconds / 60);
    const seconds = totalSeconds % 60;
    return `${String(minutes).padStart(2, "0")}:${String(seconds).padStart(2, "0")}`;
  };

  return `${formatMs(startMs)} - ${formatMs(endMs)}`;
}

function buildFallbackSummary(overview, session) {
  const questions = [...(overview?.questions ?? []), ...(overview?.risks ?? [])]
    .slice(0, 2)
    .map((item) => item.title);

  return {
    headline: overview?.current_topic || session?.title || "회의 요약이 아직 없습니다.",
    summary: overview?.current_topic
      ? [`이번 회의는 ${overview.current_topic} 중심으로 정리되었습니다.`]
      : ["아직 요약할 수 있는 회의 정리 정보가 부족합니다."],
    topics: overview?.current_topic
      ? [
          {
            title: overview.current_topic,
            summary: `${overview.current_topic} 관련 논의가 이어졌습니다.`,
            start_ms: 0,
            end_ms: 0,
          },
        ]
      : [],
    decisions: (overview?.decisions ?? []).slice(0, 3).map((item) => item.title),
    next_actions: (overview?.action_items ?? []).slice(0, 3).map((item) => ({
      title: item.title,
      owner: item.speaker_label || formatEventState(item.state),
      due_date: null,
    })),
    open_questions: questions,
    changed_since_last_meeting: [],
    evidence: [],
  };
}

function buildSummaryModel(overview, session) {
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

function buildAssistantMessages({ summary }) {
  const assistantIntro = {
    role: "assistant",
    text: "회의 요약을 기준으로 바로 확인할 질문을 보여드립니다.",
  };

  if ((summary.next_actions ?? []).length > 0) {
    const firstAction = summary.next_actions[0];
    return [
      assistantIntro,
      {
        role: "user",
        text: "지금 가장 먼저 챙겨야 할 일은 뭐야?",
      },
      {
        role: "assistant",
        text: `${firstAction.title}${firstAction.owner ? `, 담당은 ${firstAction.owner}` : ""}`,
        linkText: "리포트 보기",
      },
    ];
  }

  if ((summary.decisions ?? []).length > 0) {
    return [
      assistantIntro,
      {
        role: "user",
        text: "이번 회의에서 가장 중요한 결정은 뭐야?",
      },
      {
        role: "assistant",
        text: summary.decisions[0],
        linkText: "리포트 보기",
      },
    ];
  }

  return [
    assistantIntro,
    {
      role: "assistant",
      text: summary.headline || "아직 정리된 회의 요약이 없습니다.",
    },
  ];
}

function buildSummaryHeadline({
  actionNotice,
  hidePreviousNote,
  latestReport,
  reportStatus,
  summary,
  session,
}) {
  if (hidePreviousNote) {
    const warningReason = String(reportStatus?.warning_reason ?? "").toLowerCase();
    if (warningReason === "post_processing_stalled") {
      return "노트 생성이 멈췄습니다.";
    }
    if (warningReason === "note_correction_stalled") {
      return "노트 다듬기가 멈췄습니다.";
    }
    if (warningReason === "report_generation_stalled") {
      return "리포트 생성이 멈췄습니다.";
    }
    return actionNotice || "새 노트를 만드는 중입니다.";
  }

  if (summary?.headline) {
    return summary.headline;
  }

  if (latestReport?.content) {
    const firstLine = latestReport.content
      .split("\n")
      .map((line) => line.trim())
      .find(Boolean);
    if (firstLine) {
      return firstLine;
    }
  }

  return session?.title || "회의 요약이 아직 없습니다.";
}

function buildSummaryStatusDescription(reportStatus) {
  const warningReason = String(reportStatus?.warning_reason ?? "").toLowerCase();
  if (warningReason === "post_processing_stalled") {
    return "후처리 단계가 멈춘 상태입니다. 워커를 다시 시작하거나 노트를 다시 생성해 주세요.";
  }
  if (warningReason === "note_correction_stalled") {
    return "노트 다듬기 단계가 멈춘 상태입니다. 워커를 다시 시작하거나 노트를 다시 생성해 주세요.";
  }
  if (warningReason === "report_generation_stalled") {
    return "리포트 생성 단계가 멈춘 상태입니다. 워커를 다시 시작하거나 리포트를 다시 생성해 주세요.";
  }
  return "완료되면 핵심 요약과 후속 조치를 여기에서 바로 확인할 수 있습니다.";
}

export default function WorkspaceInsightPanel({
  actionNotice,
  hidePreviousNote,
  latestReport,
  onOpenDetail,
  overview,
  reportStatus,
  session,
  sessionId,
}) {
  const summary = buildSummaryModel(overview, session);
  const summaryHeadline = buildSummaryHeadline({
    actionNotice,
    hidePreviousNote,
    latestReport,
    reportStatus,
    summary,
    session,
  });
  const assistantMessages = buildAssistantMessages({ summary });

  return (
    <aside className="caps-insight-panel">
      <div className="caps-summary-block">
        <div className="caps-summary-header">
          <h3>회의 요약</h3>
          <span className={`caps-status-badge ${getMeetingStatusTone(reportStatus, session)}`}>
            {getMeetingStatusLabel(reportStatus, session)}
          </span>
        </div>

        {hidePreviousNote ? (
          <div className="caps-summary-status-card">
            <strong>{summaryHeadline}</strong>
            <p>{buildSummaryStatusDescription(reportStatus)}</p>
          </div>
        ) : (
          <div className="caps-summary-headline">{summaryHeadline}</div>
        )}

        {!hidePreviousNote ? (
          <>
            <div className="caps-summary-section">
              <p className="caps-summary-label">핵심 요약</p>
              <ul className="caps-summary-bullets">
                {(summary.summary ?? []).slice(0, 4).map((item, index) => (
                  <li key={`summary-${index}`}>{item}</li>
                ))}
              </ul>
            </div>

            {(summary.topics ?? []).length > 0 ? (
              <div className="caps-summary-section">
                <p className="caps-summary-label">주제 흐름</p>
                <div className="caps-action-stack">
                  {summary.topics.slice(0, 4).map((item, index) => (
                    <div key={`topic-${index}`} className="caps-action-card">
                      <span>{item.title}</span>
                      <strong>{formatTimeRange(item.start_ms, item.end_ms)}</strong>
                      <p>{item.summary}</p>
                    </div>
                  ))}
                </div>
              </div>
            ) : null}

            <div className="caps-summary-section">
              <p className="caps-summary-label">확정된 것</p>
              <ul className="caps-summary-bullets">
                {(summary.decisions ?? []).slice(0, 3).map((item, index) => (
                  <li key={`decision-${index}`}>{item}</li>
                ))}
                {(summary.decisions ?? []).length === 0 ? (
                  <li>아직 정리된 결정 사항이 없습니다.</li>
                ) : null}
              </ul>
            </div>

            <div className="caps-summary-section">
              <p className="caps-summary-label">바로 할 일</p>
              <div className="caps-action-stack">
                {(summary.next_actions ?? []).slice(0, 3).map((item, index) => (
                  <div key={`action-${index}`} className="caps-action-card">
                    <span>{item.title}</span>
                    <strong>{item.owner || item.due_date || "담당 미정"}</strong>
                  </div>
                ))}
                {(summary.next_actions ?? []).length === 0 ? (
                  <div className="caps-action-card empty">
                    <span>정리된 후속 작업이 없습니다.</span>
                  </div>
                ) : null}
              </div>
            </div>

            <div className="caps-summary-section">
              <p className="caps-summary-label">남은 질문</p>
              <div className="caps-risk-stack">
                {(summary.open_questions ?? []).slice(0, 2).map((item, index) => (
                  <div key={`question-${index}`} className="caps-risk-card">
                    <AlertTriangle size={14} />
                    <span>{item}</span>
                  </div>
                ))}
                {(summary.open_questions ?? []).length === 0 ? (
                  <div className="caps-risk-card empty">
                    <AlertTriangle size={14} />
                    <span>지금 기준으로 남은 질문은 없습니다.</span>
                  </div>
                ) : null}
              </div>
            </div>

            {(summary.changed_since_last_meeting ?? []).length > 0 ? (
              <div className="caps-summary-section">
                <p className="caps-summary-label">이전 회의 대비 변경점</p>
                <ul className="caps-summary-bullets">
                  {summary.changed_since_last_meeting.slice(0, 2).map((item, index) => (
                    <li key={`changed-${index}`}>{item}</li>
                  ))}
                </ul>
              </div>
            ) : null}

            {(summary.evidence ?? []).length > 0 ? (
              <div className="caps-summary-section">
                <p className="caps-summary-label">다시 볼 구간</p>
                <div className="caps-action-stack">
                  {summary.evidence.slice(0, 3).map((item, index) => (
                    <div key={`evidence-${index}`} className="caps-action-card">
                      <span>{item.label}</span>
                      <strong>{formatTimeRange(item.start_ms, item.end_ms)}</strong>
                    </div>
                  ))}
                </div>
              </div>
            ) : null}
          </>
        ) : null}
      </div>

      {!hidePreviousNote ? (
        <div className="caps-assistant-block">
          <div className="caps-assistant-header">
            <Sparkles size={16} />
            <h3>AI 어시스턴트</h3>
          </div>

          <div className="caps-assistant-messages">
            {assistantMessages.map((message, index) => (
              <div
                key={`${message.role}-${index}`}
                className={`caps-chat-row ${message.role === "user" ? "user" : "assistant"}`}
              >
                <div className="caps-chat-bubble">
                  <p>{message.text}</p>
                  {message.linkText ? (
                    <button
                      className="caps-chat-link"
                      onClick={() =>
                        latestReport
                          ? onOpenDetail({
                              type: "report",
                              reportId: latestReport.id,
                              sessionId,
                            })
                          : null
                      }
                      type="button"
                    >
                      <FileText size={13} />
                      {message.linkText}
                    </button>
                  ) : null}
                </div>
              </div>
            ))}
          </div>

          <div className="caps-assistant-input">
            <input placeholder="AI에게 질문하기..." type="text" />
            <button type="button">
              <SendHorizontal size={15} />
            </button>
          </div>
        </div>
      ) : null}
    </aside>
  );
}
