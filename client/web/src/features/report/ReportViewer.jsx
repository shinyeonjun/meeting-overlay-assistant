/** 웹 워크스페이스의 리포트 기능 화면을 렌더링한다. */
import React from 'react';
import { FileText, Sparkles, Loader } from 'lucide-react';
import './report-viewer.css';

export default function ReportViewer({ report, isLive }) {
  if (isLive) {
    return (
      <div className="report-viewer-empty">
        <Loader className="spinner" size={32} color="var(--accent-base)" />
        <h3 style={{ marginTop: 24, marginBottom: 8 }}>회의가 진행 중입니다</h3>
        <p style={{ color: 'var(--text-tertiary)' }}>회의가 종료되면 AI 요약 리포트가 이곳에 자동으로 생성됩니다.</p>
      </div>
    );
  }

  if (!report) {
    return (
      <div className="report-viewer-empty">
        <FileText size={48} opacity={0.3} style={{ marginBottom: 24 }} />
        <h3 style={{ marginBottom: 8 }}>생성된 리포트가 없습니다</h3>
        <p style={{ color: 'var(--text-tertiary)' }}>이 세션에 대해 아직 AI가 요약한 내용이 없습니다.</p>
      </div>
    );
  }

  return (
    <div className="report-viewer">
      <div className="report-header">
        <div className="report-badge">
          <Sparkles size={14} /> AI Generated
        </div>
        <h2 className="report-title">{report.title || "회의 요약 리포트"}</h2>
        {report.generated_at && (
          <p className="report-date">생성일시: {new Date(report.generated_at).toLocaleString()}</p>
        )}
      </div>

      {report.summary && (
        <div className="report-section summary-section">
          <h3 className="section-heading">Executive Summary</h3>
          <p className="section-body">{report.summary}</p>
        </div>
      )}

      {report.sections && report.sections.map((sec, idx) => (
        <div key={idx} className="report-section">
          <h3 className="section-heading">{sec.title}</h3>
          <div className="section-body">
            {typeof sec.content === 'string' ? (
              <p>{sec.content}</p>
            ) : Array.isArray(sec.content) ? (
              <ul className="report-list">
                {sec.content.map((item, i) => <li key={i}>{item}</li>)}
              </ul>
            ) : (
              <pre>{JSON.stringify(sec.content, null, 2)}</pre>
            )}
          </div>
        </div>
      ))}
    </div>
  );
}
