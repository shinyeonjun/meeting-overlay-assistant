import React, { useEffect, useMemo, useState } from "react";
import {
  AlertCircle,
  Clock3,
  FileText,
  Loader,
  Mic,
  NotebookPen,
  Plus,
  Sparkles,
  Upload,
  Users,
  Video,
} from "lucide-react";

import { fetchSessionOverview } from "../../services/session-api.js";
import {
  enqueueReportGenerationJob,
  fetchFinalReportStatus,
  fetchLatestReport,
  fetchReportGenerationJob,
} from "../../services/report-api.js";
import {
  formatDateTime,
  formatFullDateTime,
  formatSourceLabel,
  getReportStatusLabel,
  getReportStatusTone,
  isLiveSession,
} from "../../app/workspace-model.js";
import "./workspace-canvas.css";

function sleep(ms) {
  return new Promise((resolve) => {
    window.setTimeout(resolve, ms);
  });
}

function formatDuration(startedAt, endedAt) {
  if (!startedAt) {
    return "시간 미확정";
  }
  const start = new Date(startedAt);
  const end = endedAt ? new Date(endedAt) : new Date();
  const diff = Math.max(0, end.getTime() - start.getTime());
  const totalMinutes = Math.floor(diff / 60000);
  const hours = Math.floor(totalMinutes / 60);
  const minutes = totalMinutes % 60;
  return `${String(hours).padStart(2, "0")}:${String(minutes).padStart(2, "0")}`;
}

function getSourceIcon(source) {
  if (!source) {
    return Mic;
  }
  if (source.includes("video") || source.includes("zoom") || source.includes("system")) {
    return Video;
  }
  if (source.includes("upload")) {
    return Upload;
  }
  return Mic;
}

function getSessionTone(isLive, reportStatus) {
  if (isLive) {
    return "live";
  }
  return getReportStatusTone(reportStatus?.status);
}

function getSessionBadgeLabel(isLive, reportStatus) {
  if (isLive) {
    return "SESSION ACTIVE";
  }
  return getReportStatusLabel(reportStatus?.status);
}

function getWorkflowItems(isLive, reportStatus) {
  if (isLive) {
    return [
      { text: "회의가 종료되면 워크스페이스에서 리포트를 명시적으로 생성합니다.", done: false, due: "종료 후" },
      { text: "실시간 자막과 이벤트를 보면서 중요한 메모를 정리합니다.", done: false, due: "진행 중" },
      { text: "핵심 논의 안건이 바뀌면 세션 노트에 바로 남깁니다.", done: false, due: "진행 중" },
    ];
  }

  if (reportStatus?.status === "completed") {
    return [
      { text: "최신 리포트를 열어 표현과 구조를 최종 검토합니다.", done: true, due: "완료" },
      { text: "필요하면 관련 참석자에게 리포트를 공유합니다.", done: false, due: "오늘" },
      { text: "후속 회의가 필요하면 다음 액션을 세션 메모로 남깁니다.", done: false, due: "내일" },
    ];
  }

  if (reportStatus?.status === "processing" || reportStatus?.status === "pending") {
    return [
      { text: "worker가 문서를 생성 중입니다. 잠시 후 상태를 다시 확인합니다.", done: false, due: "처리 중" },
      { text: "다른 세션으로 이동해 다음 작업을 먼저 진행할 수 있습니다.", done: false, due: "지금" },
      { text: "생성이 끝나면 최신 리포트를 열어 검토합니다.", done: false, due: "완료 후" },
    ];
  }

  if (reportStatus?.status === "failed") {
    return [
      { text: "실패 사유를 확인하고 재시도 가능 여부를 결정합니다.", done: false, due: "확인 필요" },
      { text: "녹음 파일과 세션 종료 상태를 다시 점검합니다.", done: false, due: "지금" },
      { text: "정상 경로가 복구되면 리포트를 다시 생성합니다.", done: false, due: "후속" },
    ];
  }

  return [
    { text: "세션이 종료되었고 리포트를 생성할 준비가 되어 있습니다.", done: false, due: "지금" },
    { text: "리포트 생성 후 최신 초안을 열어 핵심 결론을 검토합니다.", done: false, due: "생성 후" },
    { text: "필요한 자료와 참석자 정보를 정리해 공유를 준비합니다.", done: false, due: "오늘" },
  ];
}

function SessionMetaItem({ icon: Icon, label, value }) {
  return (
    <div className="session-meta-item">
      <p>{label}</p>
      <div className="session-meta-value">
        <Icon size={16} />
        <span>{value}</span>
      </div>
    </div>
  );
}

function ResourceItem({ icon: Icon, label, meta, onClick }) {
  return (
    <button className="session-resource-item" onClick={onClick} type="button">
      <div className="session-resource-icon">
        <Icon size={16} />
      </div>
      <div className="session-resource-copy">
        <strong>{label}</strong>
        <span>{meta}</span>
      </div>
    </button>
  );
}

export default function WorkspaceCanvas({
  sessionId,
  onOpenDetail,
  onRefreshWorkspace,
}) {
  const [overview, setOverview] = useState(null);
  const [reportStatus, setReportStatus] = useState(null);
  const [latestReport, setLatestReport] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [actionError, setActionError] = useState(null);
  const [generating, setGenerating] = useState(false);
  const [draftNotesBySession, setDraftNotesBySession] = useState({});

  const notes = draftNotesBySession[sessionId] ?? "";

  useEffect(() => {
    let cancelled = false;

    async function loadSession() {
      try {
        setLoading(true);
        setError(null);
        setActionError(null);

        const [nextOverview, nextReportStatus] = await Promise.all([
          fetchSessionOverview({ sessionId }),
          fetchFinalReportStatus({ sessionId }),
        ]);

        let nextLatestReport = null;
        if (nextReportStatus.status === "completed" && nextReportStatus.latest_report_id) {
          nextLatestReport = await fetchLatestReport({ sessionId });
        }

        if (!cancelled) {
          setOverview(nextOverview);
          setReportStatus(nextReportStatus);
          setLatestReport(nextLatestReport);
        }
      } catch (nextError) {
        if (!cancelled) {
          setError(
            nextError instanceof Error
              ? nextError.message
              : "세션 상세를 불러오지 못했습니다.",
          );
        }
      } finally {
        if (!cancelled) {
          setLoading(false);
        }
      }
    }

    void loadSession();
    return () => {
      cancelled = true;
    };
  }, [sessionId]);

  const session = overview?.session;
  const isLive = isLiveSession(session?.status);
  const sessionTone = getSessionTone(isLive, reportStatus);
  const sessionBadgeLabel = getSessionBadgeLabel(isLive, reportStatus);
  const SourceIcon = getSourceIcon(session?.primary_input_source);

  const workflowItems = useMemo(
    () => getWorkflowItems(isLive, reportStatus),
    [isLive, reportStatus],
  );

  const previewParagraphs = useMemo(() => {
    if (!latestReport?.content) {
      return [];
    }
    return latestReport.content
      .split("\n")
      .map((line) => line.trim())
      .filter(Boolean)
      .slice(0, 2);
  }, [latestReport]);

  function handleNoteChange(nextValue) {
    setDraftNotesBySession((current) => ({
      ...current,
      [sessionId]: nextValue,
    }));
  }

  async function handleGenerateReport() {
    try {
      setGenerating(true);
      setActionError(null);
      await enqueueReportGenerationJob({ sessionId });

      let completedJob = null;
      for (let attempt = 0; attempt < 25; attempt += 1) {
        const job = await fetchReportGenerationJob({ sessionId });
        if (job.status === "completed" || job.status === "failed") {
          completedJob = job;
          break;
        }
        await sleep(1500);
      }

      const nextStatus = await fetchFinalReportStatus({ sessionId });
      setReportStatus(nextStatus);
      if (nextStatus.status === "completed") {
        const nextLatestReport = await fetchLatestReport({ sessionId });
        setLatestReport(nextLatestReport);
      }
      await onRefreshWorkspace();
      if (completedJob === null) {
        setActionError("리포트 생성이 지연되고 있습니다. worker 상태를 확인한 뒤 잠시 후 다시 확인해 주세요.");
      }
    } catch (nextError) {
      setActionError(
        nextError instanceof Error
          ? nextError.message
          : "리포트 생성 요청에 실패했습니다.",
      );
    } finally {
      setGenerating(false);
    }
  }

  if (loading) {
    return (
      <div className="workspace-state-view">
        <Loader className="spinner" size={28} />
        <p>세션 상세를 불러오는 중입니다.</p>
      </div>
    );
  }

  if (error || !overview || !session) {
    return (
      <div className="workspace-state-view error">
        <AlertCircle size={28} />
        <h3>세션 상세를 열지 못했습니다.</h3>
        <p>{error}</p>
      </div>
    );
  }

  return (
    <div className="session-workbench animate-fade-in">
      <div className="session-workbench-header">
        <div className="session-workbench-title-block">
          <div className="session-workbench-badges">
            <span className={`session-chip ${sessionTone}`}>{sessionBadgeLabel}</span>
            <span className="session-chip subtle">#{session.id.slice(0, 12)}</span>
          </div>
          <h1>{session.title || "제목 없는 세션"}</h1>
        </div>

        <div className="session-header-actions">
          <button
            className="session-action-button secondary"
            onClick={() => onOpenDetail({ type: "session", sessionId })}
            type="button"
          >
            세션 보기
          </button>
          {reportStatus?.status === "completed" && latestReport ? (
            <button
              className="session-action-button primary"
              onClick={() =>
                onOpenDetail({
                  type: "report",
                  sessionId,
                  reportId: latestReport.id,
                })
              }
              type="button"
            >
              <Sparkles size={15} />
              최신 리포트
            </button>
          ) : (
            <button
              className="session-action-button primary"
              disabled={generating || isLive || reportStatus?.status === "processing" || reportStatus?.status === "pending"}
              onClick={handleGenerateReport}
              type="button"
            >
              {generating ? (
                <>
                  <Loader size={15} className="spinner" />
                  생성 중
                </>
              ) : (
                <>
                  <Sparkles size={15} />
                  리포트 생성
                </>
              )}
            </button>
          )}
        </div>
      </div>

      <div className="session-meta-grid">
        <SessionMetaItem
          icon={SourceIcon}
          label="입력 소스"
          value={formatSourceLabel(session.primary_input_source)}
        />
        <SessionMetaItem
          icon={Clock3}
          label="시작 시간"
          value={formatFullDateTime(session.started_at)}
        />
        <SessionMetaItem
          icon={Clock3}
          label="진행 시간"
          value={`${formatDuration(session.started_at, session.ended_at)}${isLive ? " (진행중)" : ""}`}
        />
        <SessionMetaItem
          icon={Users}
          label="참석자"
          value={session.participant_count ? `${session.participant_count}명` : "참석자 미확정"}
        />
      </div>

      {actionError ? <div className="inline-banner error">{actionError}</div> : null}

      <div className="session-workbench-grid">
        <div className="session-main-column">
          <section className="session-block">
            <div className="session-block-title">
              <FileText size={17} />
              <h3>최신 리포트 (초안)</h3>
            </div>
            <div className="session-preview-card">
              <div className="session-preview-watermark">
                <FileText size={56} />
              </div>
              <div className="session-preview-content">
                {previewParagraphs.length > 0 ? (
                  <>
                    {previewParagraphs.map((paragraph) => (
                      <p key={paragraph}>{paragraph}</p>
                    ))}
                    <div className="session-preview-tags">
                      <span>{overview.current_topic || "핵심 안건 정리"}</span>
                      <span>{getReportStatusLabel(reportStatus?.status)}</span>
                    </div>
                  </>
                ) : (
                  <>
                    <div className="session-preview-skeleton short" />
                    <div className="session-preview-skeleton medium" />
                    <div className="session-preview-skeleton long" />
                  </>
                )}
              </div>
            </div>
          </section>

          <section className="session-block">
            <div className="session-block-title">
              <NotebookPen size={17} />
              <h3>세션 작업 노트</h3>
            </div>
            <div className="session-note-panel">
              <textarea
                onChange={(event) => handleNoteChange(event.target.value)}
                placeholder="회의 중 중요한 메모를 입력하세요..."
                spellCheck={false}
                value={notes}
              />
            </div>
          </section>
        </div>

        <aside className="session-side-column">
          <section className="session-side-block">
            <h3>다음 작업 (Next Actions)</h3>
            <ul className="session-checklist">
              {workflowItems.map((item) => (
                <li key={item.text} className={item.done ? "done" : ""}>
                  <span className="session-check-icon">
                    {item.done ? <Sparkles size={13} /> : <Plus size={13} />}
                  </span>
                  <div>
                    <p>{item.text}</p>
                    <span>{item.due}</span>
                  </div>
                </li>
              ))}
            </ul>
          </section>

          <section className="session-side-block">
            <h3>파일 및 리소스</h3>
            <div className="session-resource-list">
              {latestReport ? (
                <ResourceItem
                  icon={FileText}
                  label={`${latestReport.report_type}.md`}
                  meta={formatDateTime(latestReport.generated_at)}
                  onClick={() =>
                    onOpenDetail({
                      type: "report",
                      sessionId,
                      reportId: latestReport.id,
                    })
                  }
                />
              ) : null}
              <ResourceItem
                icon={SourceIcon}
                label={formatSourceLabel(session.primary_input_source)}
                meta={session.ended_at ? "세션 원본 연결됨" : "실시간 입력 중"}
                onClick={() => onOpenDetail({ type: "session", sessionId })}
              />
              <ResourceItem
                icon={NotebookPen}
                label="현재 세션 작업 노트"
                meta={notes ? "작성 중" : "노트 비어 있음"}
                onClick={() => {}}
              />
            </div>
          </section>

          <section className="session-side-block compact">
            <h3>현재 요약</h3>
            <p className="session-summary-copy">
              {overview.current_topic || "아직 정리된 현재 주제가 없습니다. 리포트 초안이 생성되면 핵심 요약이 이 영역을 채웁니다."}
            </p>
          </section>
        </aside>
      </div>
    </div>
  );
}
