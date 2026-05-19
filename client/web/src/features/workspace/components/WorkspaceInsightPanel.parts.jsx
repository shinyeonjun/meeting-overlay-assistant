import React from "react";
import { AlertTriangle, Loader2 } from "lucide-react";

import { getMeetingStatusLabel, getMeetingStatusTone } from "../../../app/workspace-model.js";
import { formatTimeRange } from "./WorkspaceInsightPanel.helpers.js";

export function InsightHeader({ reportStatus, session }) {
  return (
    <div className="caps-summary-header">
      <h3>노트 인사이트</h3>
      <span className={`caps-status-badge ${getMeetingStatusTone(reportStatus, session)}`}>
        {getMeetingStatusLabel(reportStatus, session)}
      </span>
    </div>
  );
}

export function InsightStatusCard({ isAnalyzing, statusCopy, workspaceSummaryStatus }) {
  return (
    <div className="caps-summary-status-card">
      <strong>
        {isAnalyzing ? <Loader2 className="spinner" size={14} /> : null}
        {statusCopy.title}
      </strong>
      <p>{statusCopy.description}</p>
      {workspaceSummaryStatus?.error_message ? (
        <p>{workspaceSummaryStatus.error_message}</p>
      ) : null}
    </div>
  );
}

export function BulletList({ emptyText, items }) {
  const normalizedItems = (items ?? []).filter(Boolean);
  if (normalizedItems.length === 0) {
    return (
      <ul className="caps-summary-bullets">
        <li>{emptyText}</li>
      </ul>
    );
  }
  return (
    <ul className="caps-summary-bullets">
      {normalizedItems.slice(0, 4).map((item, index) => (
        <li key={`${emptyText}-${index}`}>{item}</li>
      ))}
    </ul>
  );
}

export function CompletedInsightContent({ summary }) {
  return (
    <>
      <div className="caps-summary-section">
        <p className="caps-summary-label">핵심 요약</p>
        <BulletList
          emptyText="정리된 요약이 없습니다."
          items={summary.summary}
        />
      </div>

      {(summary.topics ?? []).length > 0 ? <TopicFlow topics={summary.topics} /> : null}

      <div className="caps-summary-section">
        <p className="caps-summary-label">결정 사항</p>
        <BulletList
          emptyText="정리된 결정 사항이 없습니다."
          items={summary.decisions}
        />
      </div>

      <NextActions actions={summary.next_actions} />
      <OpenQuestions questions={summary.open_questions} />
    </>
  );
}

function TopicFlow({ topics }) {
  return (
    <div className="caps-summary-section">
      <p className="caps-summary-label">주제 흐름</p>
      <div className="caps-action-stack">
        {topics.slice(0, 4).map((item, index) => (
          <div key={`topic-${index}`} className="caps-action-card">
            <span>{item.title}</span>
            <strong>{formatTimeRange(item.start_ms, item.end_ms)}</strong>
            <p>{item.summary}</p>
          </div>
        ))}
      </div>
    </div>
  );
}

function NextActions({ actions }) {
  return (
    <div className="caps-summary-section">
      <p className="caps-summary-label">다음 할 일</p>
      <div className="caps-action-stack">
        {(actions ?? []).slice(0, 3).map((item, index) => (
          <div key={`action-${index}`} className="caps-action-card">
            <span>{item.title}</span>
            <strong>{item.owner || item.due_date || "담당 미정"}</strong>
          </div>
        ))}
        {(actions ?? []).length === 0 ? (
          <div className="caps-action-card empty">
            <span>정리된 다음 할 일이 없습니다.</span>
          </div>
        ) : null}
      </div>
    </div>
  );
}

function OpenQuestions({ questions }) {
  return (
    <div className="caps-summary-section">
      <p className="caps-summary-label">남은 질문</p>
      <div className="caps-risk-stack">
        {(questions ?? []).slice(0, 2).map((item, index) => (
          <div key={`question-${index}`} className="caps-risk-card">
            <AlertTriangle size={14} />
            <span>{item}</span>
          </div>
        ))}
        {(questions ?? []).length === 0 ? (
          <div className="caps-risk-card empty">
            <AlertTriangle size={14} />
            <span>현재 기준으로 남은 질문은 없습니다.</span>
          </div>
        ) : null}
      </div>
    </div>
  );
}
