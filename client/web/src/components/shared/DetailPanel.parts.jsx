import React from "react";
import { AlertCircle, Loader } from "lucide-react";

export function MetaGrid({ items }) {
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

export function DetailLoadingState() {
  return (
    <div className="detail-state-view">
      <Loader className="spinner" size={24} />
      <p>상세 정보를 불러오는 중입니다.</p>
    </div>
  );
}

export function DetailErrorState({ message }) {
  return (
    <div className="detail-state-view error">
      <AlertCircle size={24} />
      <p>{message}</p>
    </div>
  );
}

export function ArtifactActions({ links }) {
  return (
    <div className="detail-artifact-actions">
      {links.map((item) => {
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
  );
}

export function ShareChecklist() {
  return (
    <div className="detail-checklist">
      <span>녹음 고지와 참석자 동의</span>
      <span>의결사항과 액션 아이템의 근거 발화</span>
      <span>보관 위치와 삭제 책임자</span>
      <span>외부 분석 전송 설정</span>
    </div>
  );
}

export function ReportPreviewSection({ content, previewUrls }) {
  return (
    <section className="detail-section">
      <div className="detail-section-head">
        <h3>HTML 미리보기</h3>
        {previewUrls?.sourceHref ? (
          <a
            className="detail-text-link"
            href={previewUrls.sourceHref}
            rel="noreferrer"
            target="_blank"
          >
            원본 열기
          </a>
        ) : null}
      </div>
      {previewUrls?.htmlHref ? (
        <iframe
          className="detail-html-preview"
          loading="lazy"
          sandbox=""
          src={previewUrls.htmlHref}
          title="회의록 HTML 미리보기"
        />
      ) : (
        <pre className="detail-pre">
          {content || "미리볼 회의록 산출물이 없습니다."}
        </pre>
      )}
    </section>
  );
}
