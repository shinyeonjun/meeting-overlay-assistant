import React, { useEffect, useState } from "react";
import { AlertCircle, Loader, X } from "lucide-react";

import { fetchSessionOverview } from "../../services/session-api.js";
import {
  fetchFinalReportStatus,
  fetchLatestReport,
  fetchReportDetail,
} from "../../services/report-api.js";
import {
  formatFullDateTime,
  formatSourceLabel,
  getReportStatusLabel,
  getSessionStatusLabel,
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
            throw new Error("세션 식별자가 없습니다.");
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

  return (
    <>
      <div className="detail-backdrop" onClick={onClose} />
      <aside className="detail-panel">
        <div className="detail-panel-header">
          <div>
            <span className="detail-panel-eyebrow">
              {isSession ? "SESSION DETAIL" : "REPORT DETAIL"}
            </span>
            <h2>{isSession ? session?.title || "세션 상세" : report?.report_type || "리포트 상세"}</h2>
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
                  { label: "세션 상태", value: getSessionStatusLabel(session.status) },
                  { label: "입력 소스", value: formatSourceLabel(session.primary_input_source) },
                  { label: "시작 시각", value: formatFullDateTime(session.started_at) },
                  { label: "종료 시각", value: formatFullDateTime(session.ended_at) },
                  { label: "리포트 상태", value: getReportStatusLabel(reportStatus?.status) },
                  { label: "현재 주제", value: sessionOverview.current_topic || "미정" },
                ]}
              />

              <section className="detail-section">
                <h3>세션 요약</h3>
                <p className="detail-copy">
                  이 패널은 세션을 운영 관점에서 다시 확인하는 용도입니다. 이벤트 원문이나 내부 메타
                  데이터는 메인 화면에서 숨기고, 상태와 리포트 흐름만 남겼습니다.
                </p>
              </section>
            </div>
          ) : null}

          {!loading && !error && !isSession && report ? (
            <div className="detail-content">
              <MetaGrid
                items={[
                  { label: "리포트 타입", value: report.report_type },
                  { label: "생성 시각", value: formatFullDateTime(report.generated_at) },
                ]}
              />

              <section className="detail-section">
                <h3>리포트 본문</h3>
                <pre className="detail-pre">{report.content || "본문이 없습니다."}</pre>
              </section>
            </div>
          ) : null}
        </div>
      </aside>
    </>
  );
}
