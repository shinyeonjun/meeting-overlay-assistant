import React, { useMemo } from "react";
import { ArrowRight, Clock3, FileAudio, Mic, PlayCircle } from "lucide-react";

import {
  formatDateTime,
  getReportStatusLabel,
  getReportStatusTone,
  getSessionStatusLabel,
  isLiveSession,
} from "../../app/workspace-model.js";

function SourceIcon({ source }) {
  if (source === "microphone") {
    return <Mic size={14} />;
  }
  return <FileAudio size={14} />;
}

function getReportTimestamp(report) {
  const value = Date.parse(report?.generated_at ?? "");
  return Number.isNaN(value) ? 0 : value;
}

function selectLatestReportsBySession(reports) {
  const map = {};
  for (const report of reports) {
    const current = map[report.session_id];
    if (!current) {
      map[report.session_id] = report;
      continue;
    }

    const reportTimestamp = getReportTimestamp(report);
    const currentTimestamp = getReportTimestamp(current);
    if (reportTimestamp > currentTimestamp) {
      map[report.session_id] = report;
      continue;
    }

    if (reportTimestamp === currentTimestamp && String(report.id) > String(current.id)) {
      map[report.session_id] = report;
    }
  }
  return map;
}

export default function History({ data, onOpenSession, onOpenDetail }) {
  const sessions = data?.sessions ?? [];
  const reportStatuses = data?.reportStatuses ?? {};
  const reportsBySession = useMemo(
    () => selectLatestReportsBySession(data?.reports ?? []),
    [data?.reports],
  );

  return (
    <div className="workspace-history animate-fade-in">
      <section className="section-heading-row">
        <div>
          <span className="section-kicker">SESSION ARCHIVE</span>
          <h2>세션 기록을 상태 중심으로 정리합니다.</h2>
          <p>
            종료 여부만 보는 게 아니라, 리포트 생성 가능 상태와 최근 산출물까지 함께 봐야
            실제 운영 흐름이 맞습니다.
          </p>
        </div>
      </section>

      <section className="table-panel">
        <div className="table-header">
          <strong>최근 세션 {sessions.length}개</strong>
          <span>진행, 종료, 리포트 생성 가능 상태를 한 번에 확인합니다.</span>
        </div>
        <div className="history-table">
          <div className="history-table-head">
            <span>세션</span>
            <span>진행 상태</span>
            <span>리포트 상태</span>
            <span>입력/시각</span>
            <span>액션</span>
          </div>
          <div className="history-table-body">
            {sessions.map((session) => {
              const reportStatus = reportStatuses[session.id];
              const latestReport = reportsBySession[session.id];
              return (
                <article key={session.id} className="history-row">
                  <div className="history-row-main">
                    <strong>{session.title || "제목 없는 세션"}</strong>
                    <span>{session.id}</span>
                  </div>
                  <div className="history-row-state">
                    <span className={`status-pill ${isLiveSession(session.status) ? "live" : "default"}`}>
                      {getSessionStatusLabel(session.status)}
                    </span>
                  </div>
                  <div className="history-row-state">
                    <span className={`status-pill ${getReportStatusTone(reportStatus?.status)}`}>
                      {getReportStatusLabel(reportStatus?.status)}
                    </span>
                  </div>
                  <div className="history-row-meta">
                    <span className="history-inline">
                      <SourceIcon source={session.primary_input_source} />
                      {formatDateTime(session.started_at)}
                    </span>
                  </div>
                  <div className="history-row-actions">
                    <button className="table-action-button" onClick={() => onOpenSession(session.id)} type="button">
                      <PlayCircle size={14} />
                      세션 보기
                    </button>
                    {latestReport ? (
                      <button
                        className="table-action-button subtle"
                        onClick={() =>
                          onOpenDetail({
                            type: "report",
                            sessionId: latestReport.session_id,
                            reportId: latestReport.id,
                          })
                        }
                        type="button"
                      >
                        <ArrowRight size={14} />
                        최신 리포트
                      </button>
                    ) : (
                      <span className="history-row-note">리포트 없음</span>
                    )}
                  </div>
                </article>
              );
            })}
          </div>
        </div>
      </section>

      <section className="workspace-grid">
        <section className="workspace-panel">
          <div className="panel-title-row">
            <div className="panel-title-left">
              <Clock3 size={16} />
              <h3>리포트 생성 가능 세션</h3>
            </div>
            <span>{sessions.filter((item) => reportStatuses[item.id]?.status === "ready").length}개</span>
          </div>
          <div className="linked-list">
            {sessions
              .filter((item) => reportStatuses[item.id]?.status === "ready")
              .slice(0, 6)
              .map((session) => (
                <button
                  key={session.id}
                  className="linked-row"
                  onClick={() => onOpenSession(session.id)}
                  type="button"
                >
                  <div>
                    <strong>{session.title || "제목 없는 세션"}</strong>
                    <span>{formatDateTime(session.started_at)}</span>
                  </div>
                  <ArrowRight size={14} />
                </button>
              ))}
          </div>
        </section>

        <section className="workspace-panel">
          <div className="panel-title-row">
            <div className="panel-title-left">
              <Clock3 size={16} />
              <h3>최근 완료 리포트</h3>
            </div>
            <span>{(data?.reports ?? []).length}건</span>
          </div>
          <div className="linked-list">
            {(data?.reports ?? []).slice(0, 6).map((report) => (
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
        </section>
      </section>
    </div>
  );
}
