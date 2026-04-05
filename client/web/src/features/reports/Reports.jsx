import React, { useEffect, useMemo, useState } from "react";
import {
  AlertTriangle,
  ArrowRight,
  Clock3,
  FileText,
  Loader,
  PlayCircle,
  Sparkles,
} from "lucide-react";

import {
  fetchReportGenerationJob,
  enqueueReportGenerationJob,
} from "../../services/report-api.js";
import {
  formatDateTime,
  formatSourceLabel,
  getReportStatusLabel,
  getReportStatusTone,
} from "../../app/workspace-model.js";

function sleep(ms) {
  return new Promise((resolve) => {
    window.setTimeout(resolve, ms);
  });
}

async function waitForReportCompletion(sessionId) {
  for (let attempt = 0; attempt < 25; attempt += 1) {
    const job = await fetchReportGenerationJob({ sessionId });
    if (job.status === "completed" || job.status === "failed") {
      return job;
    }
    await sleep(1500);
  }
  return null;
}

function QueueCard({ session, reportStatus, busy, onGenerate, onOpenSession }) {
  return (
    <article className="queue-card">
      <div className="queue-card-top">
        <span className={`status-pill ${getReportStatusTone(reportStatus, session)}`}>
          {getReportStatusLabel(reportStatus, session)}
        </span>
        <span className="meta-text">{formatDateTime(session.started_at)}</span>
      </div>
      <strong>{session.title || "제목 없는 세션"}</strong>
      <p>{formatSourceLabel(session.primary_input_source)}</p>
      <div className="queue-card-actions">
        <button
          className="primary-button"
          disabled={busy}
          onClick={() => onGenerate(session.id)}
          type="button"
        >
          {busy ? (
            <>
              <Loader size={16} className="spinner" />
              생성 중
            </>
          ) : (
            <>
              <Sparkles size={16} />
              리포트 생성
            </>
          )}
        </button>
        <button className="ghost-button" onClick={() => onOpenSession(session.id)} type="button">
          세션 보기
        </button>
      </div>
    </article>
  );
}

function FailedQueueRow({
  session,
  reportStatus,
  failedJob,
  busy,
  onRetry,
  onOpenSession,
}) {
  return (
    <article className="queue-card">
      <div className="queue-card-top">
        <span className={`status-pill ${getReportStatusTone(reportStatus, session)}`}>
          {getReportStatusLabel(reportStatus, session)}
        </span>
        <span className="meta-text">{formatDateTime(session.started_at)}</span>
      </div>
      <strong>{session.title || "제목 없는 세션"}</strong>
      <p>{formatSourceLabel(session.primary_input_source)}</p>
      <p className="meta-text">
        실패 사유: {failedJob?.error_message || "사유를 아직 확인하지 못했습니다."}
      </p>
      <div className="queue-card-actions">
        <button
          className="primary-button"
          disabled={busy}
          onClick={() => onRetry(session.id)}
          type="button"
        >
          {busy ? (
            <>
              <Loader size={16} className="spinner" />
              재시도 중
            </>
          ) : (
            <>
              <Sparkles size={16} />
              다시 생성
            </>
          )}
        </button>
        <button className="ghost-button" onClick={() => onOpenSession(session.id)} type="button">
          세션 보기
        </button>
      </div>
    </article>
  );
}

function LinkedStatusList({ sessions, reportStatuses, onOpenSession, emptyText }) {
  if (sessions.length === 0) {
    return <div className="panel-empty">{emptyText}</div>;
  }

  return (
    <div className="linked-list">
      {sessions.map((session) => (
        <button
          key={session.id}
          className="linked-row"
          onClick={() => onOpenSession(session.id)}
          type="button"
        >
          <div>
            <strong>{session.title || "제목 없는 세션"}</strong>
            <span>{getReportStatusLabel(reportStatuses[session.id], session)}</span>
          </div>
          <ArrowRight size={14} />
        </button>
      ))}
    </div>
  );
}

export default function Reports({
  data,
  grouped,
  onOpenSession,
  onOpenDetail,
  onRefreshWorkspace,
}) {
  const [busySessionId, setBusySessionId] = useState(null);
  const [error, setError] = useState(null);
  const [failedJobs, setFailedJobs] = useState({});

  const reportStatuses = data?.reportStatuses ?? {};
  const reports = data?.reports ?? [];
  const failed = grouped.failed ?? [];
  const failedSessionIds = useMemo(() => failed.map((session) => session.id), [failed]);

  useEffect(() => {
    let cancelled = false;

    async function loadFailedJobs() {
      if (failedSessionIds.length === 0) {
        setFailedJobs({});
        return;
      }

      const entries = await Promise.all(
        failedSessionIds.map(async (sessionId) => {
          try {
            const job = await fetchReportGenerationJob({ sessionId });
            return [sessionId, job];
          } catch {
            return [sessionId, null];
          }
        }),
      );

      if (!cancelled) {
        setFailedJobs(
          Object.fromEntries(entries.filter(([, job]) => job !== null)),
        );
      }
    }

    void loadFailedJobs();
    return () => {
      cancelled = true;
    };
  }, [failedSessionIds]);

  async function handleGenerateReport(sessionId) {
    try {
      setBusySessionId(sessionId);
      setError(null);
      await enqueueReportGenerationJob({ sessionId });
      const completedJob = await waitForReportCompletion(sessionId);
      await onRefreshWorkspace();
      if (completedJob === null) {
        setError("리포트 생성이 지연되고 있습니다. worker 상태를 확인한 뒤 잠시 후 다시 확인해 주세요.");
      }
    } catch (nextError) {
      setError(nextError instanceof Error ? nextError.message : "리포트 생성 요청에 실패했습니다.");
    } finally {
      setBusySessionId(null);
    }
  }

  return (
    <div className="reports-board animate-fade-in">
      <section className="section-heading-row">
        <div>
          <span className="section-kicker">OPERATIONS DESK</span>
          <h2>문서 생성 상태와 실패한 작업을 운영 관점에서 모아봅니다.</h2>
          <p>
            `운영`은 회의를 읽는 곳이 아니라, 생성 대기, worker 처리, 실패 재시도 같은 상태를
            점검하는 보드입니다.
          </p>
        </div>
      </section>

      {error ? <div className="inline-banner error">{error}</div> : null}

      <div className="workspace-grid reports-grid">
        <section className="workspace-panel">
          <div className="panel-title-row">
            <div className="panel-title-left">
              <Sparkles size={16} />
              <h3>생성 가능 세션</h3>
            </div>
            <span>{grouped.ready.length}개</span>
          </div>
          {grouped.ready.length > 0 ? (
            <div className="queue-list">
              {grouped.ready.map((session) => (
                <QueueCard
                  key={session.id}
                  session={session}
                  reportStatus={reportStatuses[session.id]}
                  busy={busySessionId === session.id}
                  onGenerate={handleGenerateReport}
                  onOpenSession={onOpenSession}
                />
              ))}
            </div>
          ) : (
            <div className="panel-empty">지금 생성 가능한 세션이 없습니다.</div>
          )}
        </section>

        <section className="workspace-panel">
          <div className="panel-title-row">
            <div className="panel-title-left">
              <Clock3 size={16} />
              <h3>처리 중 작업</h3>
            </div>
            <span>{grouped.processing.length}개</span>
          </div>
          <LinkedStatusList
            sessions={grouped.processing}
            reportStatuses={reportStatuses}
            onOpenSession={onOpenSession}
            emptyText="현재 처리 중인 리포트 job이 없습니다."
          />
        </section>
      </div>

      <div className="workspace-grid reports-grid">
        <section className="workspace-panel">
          <div className="panel-title-row">
            <div className="panel-title-left">
              <AlertTriangle size={16} />
              <h3>실패한 작업</h3>
            </div>
            <span>{failed.length}개</span>
          </div>
          {failed.length > 0 ? (
            <div className="queue-list">
              {failed.map((session) => (
                <FailedQueueRow
                  key={session.id}
                  session={session}
                  reportStatus={reportStatuses[session.id]}
                  failedJob={failedJobs[session.id]}
                  busy={busySessionId === session.id}
                  onRetry={handleGenerateReport}
                  onOpenSession={onOpenSession}
                />
              ))}
            </div>
          ) : (
            <div className="panel-empty">실패한 작업이 없습니다.</div>
          )}
        </section>

        <section className="workspace-panel">
          <div className="panel-title-row">
            <div className="panel-title-left">
              <PlayCircle size={16} />
              <h3>생성 전 체크</h3>
            </div>
          </div>
          <div className="checklist-list">
            <div className="checklist-row">이벤트 주체가 누락되지 않았는지</div>
            <div className="checklist-row">세션 제목과 실제 논의 내용이 맞는지</div>
            <div className="checklist-row">speaker transcript가 읽을 만한지</div>
            <div className="checklist-row">assistant 검색에 재활용할 문장이 있는지</div>
          </div>
        </section>
      </div>

      <section className="workspace-panel">
        <div className="panel-title-row">
          <div className="panel-title-left">
            <FileText size={16} />
            <h3>최근 생성된 리포트</h3>
          </div>
          <span>{reports.length}건</span>
        </div>
        {reports.length > 0 ? (
          <div className="linked-list">
            {reports.map((report) => (
              <button
                key={report.id}
                className="linked-row"
                onClick={() =>
                  onOpenDetail({
                    type: "report",
                    sessionId: report.session_id,
                    reportId: report.id,
                  })
                }
                type="button"
              >
                <div>
                  <strong>{report.report_type}</strong>
                  <span>{formatDateTime(report.generated_at)}</span>
                </div>
                <ArrowRight size={14} />
              </button>
            ))}
          </div>
        ) : (
          <div className="panel-empty">생성된 리포트가 아직 없습니다.</div>
        )}
      </section>

      <section className="workspace-panel">
        <div className="panel-title-row">
          <div className="panel-title-left">
            <PlayCircle size={16} />
            <h3>최근 회의 상태</h3>
          </div>
          <span>{(data?.sessions ?? []).length}건</span>
        </div>
        {(data?.sessions ?? []).length > 0 ? (
          <div className="linked-list">
            {(data?.sessions ?? []).slice(0, 8).map((session) => (
              <button
                key={session.id}
                className="linked-row"
                onClick={() => onOpenSession(session.id)}
                type="button"
              >
                <div>
                  <strong>{session.title || "제목 없는 회의"}</strong>
                  <span>
                    {formatDateTime(session.started_at)} · {formatSourceLabel(session.primary_input_source)}
                  </span>
                </div>
                <ArrowRight size={14} />
              </button>
            ))}
          </div>
        ) : (
          <div className="panel-empty">최근 회의가 없습니다.</div>
        )}
      </section>
    </div>
  );
}
