import React, { useEffect, useState } from "react";
import { X } from "lucide-react";

import { fetchSessionOverview } from "../../services/session-api.js";
import {
  fetchFinalReportStatus,
  fetchLatestReport,
  fetchReportDetail,
} from "../../services/report-api.js";
import {
  formatFullDateTime,
  formatSourceLabel,
  getSessionStatusLabel,
  resolveWorkflowStatus,
} from "../../app/workspace-model.js";
import {
  buildReportArtifactLinks,
  buildReportPreviewUrls,
  resolveSessionId,
} from "./DetailPanel.helpers.js";
import {
  ArtifactActions,
  DetailErrorState,
  DetailLoadingState,
  MetaGrid,
  ReportPreviewSection,
  ShareChecklist,
} from "./DetailPanel.parts.jsx";
import "./detail-panel.css";

export default function DetailPanel({ config, onClose }) {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  useEffect(() => {
    if (!config) {
      return undefined;
    }

    let cancelled = false;

    async function loadDetail() {
      try {
        setLoading(true);
        setError(null);
        setData(null);

        const nextData =
          config.type === "session"
            ? await loadSessionDetail(config)
            : await loadReportDetail(config);
        if (!cancelled) {
          setData(nextData);
        }
      } catch (nextError) {
        if (!cancelled) {
          setError(
            nextError instanceof Error
              ? nextError.message
              : "상세 데이터를 불러오지 못했습니다.",
          );
        }
      } finally {
        if (!cancelled) {
          setLoading(false);
        }
      }
    }

    void loadDetail();
    return () => {
      cancelled = true;
    };
  }, [config]);

  if (!config) {
    return null;
  }

  const isSession = config.type === "session";
  const sessionOverview = data?.overview;
  const session = sessionOverview?.session;
  const reportStatus = data?.reportStatus;
  const report = data?.report;
  const workflow = resolveWorkflowStatus(session, reportStatus);

  return (
    <>
      <div className="detail-backdrop" onClick={onClose} />
      <aside className="detail-panel">
        <div className="detail-panel-header">
          <div>
            <span className="detail-panel-eyebrow">
              {isSession ? "회의 상세" : "회의록 산출물"}
            </span>
            <h2>
              {isSession ? session?.title || "회의 상세" : report?.report_type || "회의록"}
            </h2>
          </div>
          <button className="detail-close-button" onClick={onClose} type="button">
            <X size={18} />
          </button>
        </div>

        <div className="detail-panel-body">
          {loading ? <DetailLoadingState /> : null}
          {error ? <DetailErrorState message={error} /> : null}

          {!loading && !error && isSession && session ? (
            <SessionDetailContent
              session={session}
              sessionOverview={sessionOverview}
              workflow={workflow}
            />
          ) : null}

          {!loading && !error && !isSession && report ? (
            <ReportDetailContent report={report} />
          ) : null}
        </div>
      </aside>
    </>
  );
}

async function loadSessionDetail(config) {
  const sessionId = resolveSessionId(config);
  if (!sessionId) {
    throw new Error("회의 식별자가 없습니다.");
  }
  const [overview, reportStatus] = await Promise.all([
    fetchSessionOverview({ sessionId }),
    fetchFinalReportStatus({ sessionId }),
  ]);
  return { overview, reportStatus };
}

async function loadReportDetail(config) {
  const report = config.reportId
    ? await fetchReportDetail({
        sessionId: config.sessionId,
        reportId: config.reportId,
      })
    : await fetchLatestReport({ sessionId: config.sessionId });
  return { report };
}

function SessionDetailContent({ session, sessionOverview, workflow }) {
  return (
    <div className="detail-content">
      <MetaGrid
        items={[
          { label: "회의 상태", value: getSessionStatusLabel(session) },
          { label: "입력 소스", value: formatSourceLabel(session.primary_input_source) },
          { label: "시작 시각", value: formatFullDateTime(session.started_at) },
          { label: "종료 시각", value: formatFullDateTime(session.ended_at) },
          { label: "정리 상태", value: workflow.label },
          { label: "현재 주제", value: sessionOverview.current_topic || "미정" },
        ]}
      />

      <section className="detail-section">
        <h3>회의 요약</h3>
        <p className="detail-copy">
          이 영역은 회의 정리 상태를 빠르게 다시 확인하는 용도입니다. 정식
          회의 내용과 회의록은 메인 회의 화면에서 확인하는 흐름을 기준으로
          유지합니다.
        </p>
      </section>
    </div>
  );
}

function ReportDetailContent({ report }) {
  const artifactLinks = buildReportArtifactLinks(report);
  const previewUrls = buildReportPreviewUrls(report);

  return (
    <div className="detail-content">
      <MetaGrid
        items={[
          { label: "파일 형식", value: report.report_type },
          { label: "생성 시각", value: formatFullDateTime(report.generated_at) },
          { label: "분석 출처", value: report.insight_source },
          { label: "버전", value: `v${report.version}` },
        ]}
      />

      <div className="detail-trust-note">
        자동 생성 문서입니다. 공유나 확정 전에 근거 구간과 원문 발화를 확인하세요.
      </div>

      <ArtifactActions links={artifactLinks} />

      <section className="detail-section">
        <h3>공유 전 확인</h3>
        <ShareChecklist />
      </section>

      <ReportPreviewSection content={report.content} previewUrls={previewUrls} />
    </div>
  );
}
