import React, { useEffect, useState } from "react";
import { AlertCircle, Download, ExternalLink, Loader, X } from "lucide-react";

import { fetchSessionOverview } from "../../services/session-api.js";
import {
  buildReportArtifactUrl,
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
import "./detail-panel.css";

function resolveSessionId(config) {
  return config?.sessionId ?? config?.id ?? null;
}

function MetaGrid({ items }) {
  return (
    <div className="detail-meta-grid">
      {items.map((item) => (
        <div key={item.label} className="detail-meta-card">
          <span>{item.label}</span>
          <strong>{item.value}</strong>
        </div>
      ))}
    </div>
  );
}

function buildReportArtifactLinks(report) {
  if (!report?.session_id || !report?.id) {
    return [];
  }

  const base = {
    reportId: report.id,
    sessionId: report.session_id,
  };
  const isPdf = report.report_type === "pdf";
  const sourceLabel = isPdf ? "PDF 미리보기" : "Markdown 열기";
  const downloadLabel = isPdf ? "PDF 다운로드" : "Markdown 다운로드";
  return [
    {
      href: buildReportArtifactUrl({ ...base, artifactKind: "source" }),
      icon: ExternalLink,
      label: sourceLabel,
    },
    {
      href: buildReportArtifactUrl({ ...base, artifactKind: "html" }),
      icon: ExternalLink,
      label: "HTML 회의록",
    },
    {
      href: buildReportArtifactUrl({ ...base, artifactKind: "source", download: true }),
      icon: Download,
      label: downloadLabel,
    },
  ];
}

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

        if (config.type === "session") {
          const sessionId = resolveSessionId(config);
          if (!sessionId) {
            throw new Error("회의 식별자가 없습니다.");
          }
          const [overview, reportStatus] = await Promise.all([
            fetchSessionOverview({ sessionId }),
            fetchFinalReportStatus({ sessionId }),
          ]);
          if (!cancelled) {
            setData({ overview, reportStatus });
          }
          return;
        }

        if (config.type === "report") {
          const report = config.reportId
            ? await fetchReportDetail({
                sessionId: config.sessionId,
                reportId: config.reportId,
              })
            : await fetchLatestReport({ sessionId: config.sessionId });
          if (!cancelled) {
            setData({ report });
          }
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
  const reportArtifactLinks = buildReportArtifactLinks(report);

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
          {loading ? (
            <div className="detail-state-view">
              <Loader className="spinner" size={24} />
              <p>상세 정보를 불러오는 중입니다.</p>
            </div>
          ) : null}

          {error ? (
            <div className="detail-state-view error">
              <AlertCircle size={24} />
              <p>{error}</p>
            </div>
          ) : null}

          {!loading && !error && isSession && session ? (
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
          ) : null}

          {!loading && !error && !isSession && report ? (
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

              <div className="detail-artifact-actions">
                {reportArtifactLinks.map((item) => {
                  const Icon = item.icon;
                  return (
                    <a
                      key={item.label}
                      className="detail-artifact-link"
                      href={item.href}
                      rel="noreferrer"
                      target="_blank"
                    >
                      <Icon size={14} />
                      {item.label}
                    </a>
                  );
                })}
              </div>

              <section className="detail-section">
                <h3>공유 전 확인</h3>
                <div className="detail-checklist">
                  <span>녹음 고지와 참석자 동의</span>
                  <span>의결사항과 액션 아이템의 근거 발화</span>
                  <span>보관 위치와 삭제 책임자</span>
                  <span>외부 AI 전송 설정</span>
                </div>
              </section>

              <section className="detail-section">
                <h3>본문 미리보기</h3>
                <pre className="detail-pre">
                  {report.content ||
                    "PDF 회의록은 상단의 PDF 미리보기 버튼으로 확인하세요."}
                </pre>
              </section>
            </div>
          ) : null}
        </div>
      </aside>
    </>
  );
}
