import React, { useMemo, useState } from "react";
import {
  FileDown,
  Loader,
  Pencil,
  RefreshCcw,
} from "lucide-react";

import {
  formatDateTime,
  formatSourceLabel,
  getMeetingStatusLabel,
  getMeetingStatusTone,
} from "../../../app/workspace-model.js";
import {
  fetchReportDocument,
  saveReportDocument,
} from "../../../services/report-api.js";

function formatDuration(ms) {
  const totalSeconds = Math.max(0, Math.floor(Number(ms || 0) / 1000));
  if (!totalSeconds) {
    return "-";
  }
  const hours = Math.floor(totalSeconds / 3600);
  const minutes = Math.floor((totalSeconds % 3600) / 60);
  if (hours > 0) {
    return `${hours}시간 ${minutes}분`;
  }
  return `${minutes || 1}분`;
}

function formatTimestamp(ms) {
  const totalSeconds = Math.max(0, Math.floor(Number(ms || 0) / 1000));
  const minutes = String(Math.floor(totalSeconds / 60)).padStart(2, "0");
  const seconds = String(totalSeconds % 60).padStart(2, "0");
  return `${minutes}:${seconds}`;
}

function normalizeTextList(items, fallback = []) {
  const normalized = (items ?? [])
    .map((item) => {
      if (typeof item === "string") {
        return item;
      }
      return item?.title || item?.text || item?.task || item?.summary || "";
    })
    .map((item) => item.trim())
    .filter(Boolean);
  return normalized.length > 0 ? normalized : fallback;
}

function normalizeActionItems(summary, overview) {
  const source = summary?.next_actions?.length
    ? summary.next_actions
    : (overview?.action_items ?? []);
  return source.slice(0, 5).map((item, index) => ({
    id: item.id || item.event_id || `${item.title || item.task}-${index}`,
    title: item.title || item.task || "후속 작업",
    owner: item.owner || item.speaker_label || "담당 미정",
    dueDate: item.due_date || item.due || "",
  }));
}

function buildFallbackLine(visibleLatestReport) {
  return visibleLatestReport?.content
    ?.split("\n")
    .map((line) => line.replace(/^#+\s*/, "").trim())
    .find((line) => line.length > 20);
}

function buildRecapModel(overview, visibleLatestReport) {
  const summary = overview?.workspace_summary;
  const fallbackOverview = buildFallbackLine(visibleLatestReport);
  const overviewLines = normalizeTextList(
    summary?.summary,
    fallbackOverview ? [fallbackOverview] : [],
  );
  const topics = (summary?.topics ?? []).slice(0, 6).map((topic) => ({
    title: topic.title || "핵심 논의",
    summary: topic.summary || topic.direction || "",
    startMs: topic.start_ms,
    endMs: topic.end_ms,
  }));

  return {
    overviewLines:
      overviewLines.length > 0
        ? overviewLines
        : ["회의록이 생성되면 핵심 정리가 이곳에 표시됩니다."],
    topics,
    decisions: normalizeTextList(
      summary?.decisions,
      (overview?.decisions ?? []).map((item) => item.title),
    ),
    actions: normalizeActionItems(summary, overview),
    openQuestions: normalizeTextList(summary?.open_questions),
  };
}

function getSpeakerLabels(reportDetail) {
  return Array.from(
    new Set(
      (reportDetail?.speaker_transcript ?? [])
        .map((item) => item.speaker_label)
        .filter(Boolean),
    ),
  );
}

function getTranscriptMeta(reportDetail) {
  const segments = reportDetail?.speaker_transcript ?? [];
  const durationMs = Math.max(...segments.map((item) => Number(item.end_ms ?? 0)), 0);
  const speakers = getSpeakerLabels(reportDetail);

  return {
    duration: formatDuration(durationMs),
    participants: speakers.length > 0 ? speakers.join(", ") : "-",
    participantsCount: speakers.length || "-",
  };
}

function buildAgenda(recap, session) {
  const firstTopic = recap.topics.find((topic) => topic.title)?.title;
  const headline = session?.title || "";
  return firstTopic || headline || "회의 안건";
}

function getSessionSourceLabel(session) {
  return formatSourceLabel(
    session?.primary_input_source ||
      session?.input_source ||
      session?.source ||
      session?.recording_source,
  );
}

function ToolbarLink({ children, className = "", disabled = false, href, primary = false }) {
  const classes = [
    "caps-minutes-toolbar-button",
    primary ? "primary" : "",
    className,
  ]
    .filter(Boolean)
    .join(" ");

  if (!href || disabled) {
    return (
      <button className={classes} disabled type="button">
        {children}
      </button>
    );
  }

  return (
    <a className={classes} href={href} rel="noreferrer" target="_blank">
      {children}
    </a>
  );
}

const EDITABLE_SECTION_GROUPS = [
  ["background", "논의 배경"],
  ["opinions", "주요 의견"],
  ["review", "검토 내용"],
  ["direction", "정리된 방향"],
];

function cloneEditableDocument(document) {
  return {
    title: document?.title || "회의록",
    metadata: Array.isArray(document?.metadata) ? document.metadata : [],
    summary: Array.isArray(document?.summary) ? document.summary : [],
    agenda: Array.isArray(document?.agenda) ? document.agenda : [],
    sections: Array.isArray(document?.sections) ? document.sections : [],
    decisions: Array.isArray(document?.decisions) ? document.decisions : [],
    action_items: Array.isArray(document?.action_items) ? document.action_items : [],
    risks: Array.isArray(document?.risks) ? document.risks : [],
    questions: Array.isArray(document?.questions) ? document.questions : [],
    discussion: Array.isArray(document?.discussion) ? document.discussion : [],
    transcript_excerpt: Array.isArray(document?.transcript_excerpt) ? document.transcript_excerpt : [],
    speaker_insights: Array.isArray(document?.speaker_insights) ? document.speaker_insights : [],
  };
}

function listItemsToText(items) {
  return (items ?? [])
    .map((item) => (typeof item === "string" ? item : item?.text || item?.task || ""))
    .filter(Boolean)
    .join("\n");
}

function textToListItems(value) {
  return String(value ?? "")
    .split("\n")
    .map((line) => line.trim())
    .filter(Boolean)
    .map((text) => ({ text }));
}

function actionItemsToText(items) {
  return (items ?? [])
    .map((item) => item?.task || item?.text || "")
    .filter(Boolean)
    .join("\n");
}

function textToActionItems(value) {
  return String(value ?? "")
    .split("\n")
    .map((line) => line.trim())
    .filter(Boolean)
    .map((task) => ({ task }));
}

function getMetaValue(document, label) {
  return (document?.metadata ?? []).find((item) => item?.label === label)?.value || "";
}

function setMetaValue(document, label, value) {
  const metadata = [...(document?.metadata ?? [])];
  const index = metadata.findIndex((item) => item?.label === label);
  if (index >= 0) {
    metadata[index] = { ...metadata[index], value };
  } else {
    metadata.push({ label, value });
  }
  return {
    ...document,
    title: label === "회의제목" ? value || "회의록" : document.title,
    metadata,
  };
}

function updateSection(document, sectionIndex, updater) {
  const sections = [...(document?.sections ?? [])];
  const current = sections[sectionIndex] ?? { title: "" };
  sections[sectionIndex] = updater(current);
  return {
    ...document,
    sections,
  };
}

function ReportEditorPanel({
  document,
  error,
  loading,
  onChange,
  onClose,
  onSave,
  saving,
}) {
  const [activeSectionIndex, setActiveSectionIndex] = useState(0);
  const sections = document?.sections ?? [];
  const activeIndex = sections.length > 0 ? Math.min(activeSectionIndex, sections.length - 1) : 0;
  const activeSection = sections[activeIndex] ?? null;

  if (!document) {
    return (
      <aside className="caps-minutes-editor-panel" aria-label="회의록 편집">
        <div className="caps-minutes-editor-header">
          <div>
            <strong>회의록 편집</strong>
            <p>편집 데이터를 불러오는 중입니다.</p>
          </div>
          <button onClick={onClose} type="button">닫기</button>
        </div>
      </aside>
    );
  }

  return (
    <aside className="caps-minutes-editor-panel" aria-label="회의록 편집">
      <div className="caps-minutes-editor-header">
        <div>
          <strong>회의록 편집</strong>
          <p>저장하면 새 PDF 버전이 생성됩니다.</p>
        </div>
        <button onClick={onClose} type="button">닫기</button>
      </div>

      {error ? <div className="caps-inline-alert">{error}</div> : null}

      <div className="caps-minutes-editor-body">
        <label className="caps-editor-field">
          <span>회의 제목</span>
          <input
            disabled={loading || saving}
            onChange={(event) => onChange(setMetaValue(document, "회의제목", event.target.value))}
            value={getMetaValue(document, "회의제목")}
          />
        </label>

        <div className="caps-editor-meta-grid">
          {["일시", "장소", "참석자"].map((label) => (
            <label className="caps-editor-field" key={label}>
              <span>{label}</span>
              <input
                disabled={loading || saving}
                onChange={(event) => onChange(setMetaValue(document, label, event.target.value))}
                value={getMetaValue(document, label)}
              />
            </label>
          ))}
        </div>

        <label className="caps-editor-field">
          <span>안건</span>
          <textarea
            disabled={loading || saving}
            onChange={(event) => onChange({ ...document, agenda: textToListItems(event.target.value) })}
            rows={2}
            value={listItemsToText(document.agenda)}
          />
        </label>

        <div className="caps-editor-section-workspace">
          <nav className="caps-editor-section-nav" aria-label="소주제 목록">
            <div className="caps-editor-section-nav-head">
              <strong>회의내용</strong>
              <span>{sections.length}개</span>
            </div>
            {sections.map((section, sectionIndex) => (
              <button
                className={sectionIndex === activeIndex ? "active" : ""}
                key={`${section.title}-${sectionIndex}`}
                onClick={() => setActiveSectionIndex(sectionIndex)}
                type="button"
              >
                <span>소주제 {sectionIndex + 1}</span>
                <strong>{section.title || "제목 없음"}</strong>
              </button>
            ))}
            <button
              className="caps-editor-add-section"
              disabled={loading || saving}
              onClick={() => {
                onChange({
                  ...document,
                  sections: [
                    ...sections,
                    {
                      title: "새 소주제",
                      background: [],
                      opinions: [],
                      review: [],
                      direction: [],
                    },
                  ],
                });
                setActiveSectionIndex(sections.length);
              }}
              type="button"
            >
              소주제 추가
            </button>
          </nav>

          {activeSection ? (
            <section className="caps-editor-section-card">
              <div className="caps-editor-section-title-row">
                <label className="caps-editor-field">
                  <span>소주제 {activeIndex + 1}</span>
                  <input
                    disabled={loading || saving}
                    onChange={(event) =>
                      onChange(
                        updateSection(document, activeIndex, (current) => ({
                          ...current,
                          title: event.target.value,
                        })),
                      )
                    }
                    value={activeSection.title || ""}
                  />
                </label>
                <button
                  disabled={loading || saving || sections.length <= 1}
                  onClick={() => {
                    onChange({
                      ...document,
                      sections: sections.filter((_, index) => index !== activeIndex),
                    });
                    setActiveSectionIndex(Math.max(0, activeIndex - 1));
                  }}
                  type="button"
                >
                  삭제
                </button>
              </div>

              {EDITABLE_SECTION_GROUPS.map(([key, label]) => (
                <label className="caps-editor-field" key={key}>
                  <span>{label}</span>
                  <textarea
                    disabled={loading || saving}
                    onChange={(event) =>
                      onChange(
                        updateSection(document, activeIndex, (current) => ({
                          ...current,
                          [key]: textToListItems(event.target.value),
                        })),
                      )
                    }
                    rows={6}
                    value={listItemsToText(activeSection[key])}
                  />
                </label>
              ))}
            </section>
          ) : (
            <div className="caps-empty-panel compact">편집할 소주제가 없습니다.</div>
          )}
        </div>

        <label className="caps-editor-field">
          <span>결정사항</span>
          <textarea
            disabled={loading || saving}
            onChange={(event) => onChange({ ...document, decisions: textToListItems(event.target.value) })}
            rows={4}
            value={listItemsToText(document.decisions)}
          />
        </label>

        <label className="caps-editor-field">
          <span>향후일정</span>
          <textarea
            disabled={loading || saving}
            onChange={(event) => onChange({ ...document, action_items: textToActionItems(event.target.value) })}
            rows={4}
            value={actionItemsToText(document.action_items)}
          />
        </label>

        <label className="caps-editor-field">
          <span>특이사항</span>
          <textarea
            disabled={loading || saving}
            onChange={(event) => onChange({ ...document, risks: textToListItems(event.target.value) })}
            rows={4}
            value={listItemsToText(document.risks)}
          />
        </label>
      </div>

      <div className="caps-minutes-editor-actions">
        <button className="caps-minutes-toolbar-button" onClick={onClose} type="button">
          취소
        </button>
        <button
          className="caps-minutes-toolbar-button primary"
          disabled={loading || saving}
          onClick={onSave}
          type="button"
        >
          {saving ? <Loader className="spinner" size={16} /> : null}
          저장 후 PDF 생성
        </button>
      </div>
    </aside>
  );
}

function EmptyLine({ children }) {
  return <p className="caps-minutes-empty">{children}</p>;
}

function MinutesSection({ children, title }) {
  return (
    <section className="caps-minutes-section">
      <h2>{title}</h2>
      {children}
    </section>
  );
}

function MinutesList({ emptyText, items, ordered = false }) {
  if (!items.length) {
    return <EmptyLine>{emptyText}</EmptyLine>;
  }

  const Tag = ordered ? "ol" : "ul";
  return (
    <Tag className="caps-minutes-list">
      {items.map((item, index) => (
        <li key={`${item}-${index}`}>{item}</li>
      ))}
    </Tag>
  );
}

function TopicBlock({ index, topic }) {
  return (
    <article className="caps-minutes-topic-block">
      <h3>
        {index + 1}. {topic.title}
      </h3>
      {topic.summary ? (
        <div className="caps-minutes-topic-body">
          <strong>정리된 내용</strong>
          <p>{topic.summary}</p>
        </div>
      ) : (
        <EmptyLine>정리된 논의 내용이 없습니다.</EmptyLine>
      )}
    </article>
  );
}

function ActionList({ actions }) {
  if (!actions.length) {
    return <EmptyLine>정리된 후속 조치가 없습니다.</EmptyLine>;
  }

  return (
    <ol className="caps-minutes-action-list">
      {actions.map((item) => (
        <li key={item.id}>
          <span>{item.title}</span>
          <em>
            {[item.owner, item.dueDate].filter(Boolean).join(" · ") || "담당 미정"}
          </em>
        </li>
      ))}
    </ol>
  );
}

function TranscriptExcerpt({ segments }) {
  if (!segments.length) {
    return <EmptyLine>교정된 대화록이 아직 없습니다.</EmptyLine>;
  }

  return (
    <div className="caps-minutes-transcript-list">
      {segments.map((segment, index) => (
        <div
          className="caps-minutes-transcript-row"
          key={segment.id || `${segment.start_ms}-${index}`}
        >
          <span>{formatTimestamp(segment.start_ms)}</span>
          <strong>{segment.speaker_label || "발화자"}</strong>
          <p>{segment.text || segment.content || ""}</p>
        </div>
      ))}
    </div>
  );
}

export default function WorkspaceRecapView({
  actionError,
  actionNotice,
  onGenerateReport,
  onReportEdited,
  overview,
  processingAction,
  reportArtifactUrls,
  reportDetail,
  reportStatus,
  reportWorkflow,
  session,
  visibleLatestReport,
}) {
  const recap = useMemo(
    () => buildRecapModel(overview, visibleLatestReport),
    [overview, visibleLatestReport],
  );
  const meta = useMemo(() => getTranscriptMeta(reportDetail), [reportDetail]);
  const transcriptSegments = useMemo(
    () => (reportDetail?.speaker_transcript ?? []).slice(0, 10),
    [reportDetail],
  );
  const statusTone = getMeetingStatusTone(reportStatus, session);
  const isReportProcessing = processingAction || reportWorkflow?.status === "processing";
  const hasReport = Boolean(visibleLatestReport?.id);
  const agenda = buildAgenda(recap, session);
  const sourceLabel = getSessionSourceLabel(session);
  const pdfPreviewHref = reportArtifactUrls?.previewHref;
  const [editorOpen, setEditorOpen] = useState(false);
  const [editDraft, setEditDraft] = useState(null);
  const [editLoading, setEditLoading] = useState(false);
  const [editSaving, setEditSaving] = useState(false);
  const [editError, setEditError] = useState(null);

  const handleOpenEditor = async () => {
    if (!session?.id || !visibleLatestReport?.id) {
      return;
    }
    setEditorOpen(true);
    setEditError(null);
    setEditLoading(true);
    try {
      const payload = await fetchReportDocument({
        sessionId: session.id,
        reportId: visibleLatestReport.id,
      });
      setEditDraft(cloneEditableDocument(payload.document));
    } catch (nextError) {
      setEditError(
        nextError instanceof Error
          ? nextError.message
          : "회의록 편집 데이터를 불러오지 못했습니다.",
      );
    } finally {
      setEditLoading(false);
    }
  };

  const handleSaveEditor = async () => {
    if (!session?.id || !visibleLatestReport?.id || !editDraft) {
      return;
    }
    setEditError(null);
    setEditSaving(true);
    try {
      await saveReportDocument({
        sessionId: session.id,
        reportId: visibleLatestReport.id,
        document: editDraft,
      });
      setEditorOpen(false);
      setEditDraft(null);
      await onReportEdited?.();
    } catch (nextError) {
      setEditError(
        nextError instanceof Error
          ? nextError.message
          : "회의록 편집본을 저장하지 못했습니다.",
      );
    } finally {
      setEditSaving(false);
    }
  };

  return (
    <div className="caps-minutes-workspace animate-fade-in">
      <div className="caps-minutes-toolbar">
        <div className="caps-minutes-toolbar-title">
          <span className={`caps-status-badge ${statusTone}`}>
            {getMeetingStatusLabel(reportStatus, session)}
          </span>
          <div>
            <strong>{session?.title || "제목 없는 회의"}</strong>
            <p>회의록 문서를 바로 확인하고 PDF로 내려받습니다.</p>
          </div>
        </div>

        <div className="caps-minutes-toolbar-actions">
          <button
            className="caps-minutes-toolbar-button"
            disabled={isReportProcessing}
            onClick={onGenerateReport}
            type="button"
          >
            {isReportProcessing ? <Loader className="spinner" size={16} /> : <RefreshCcw size={16} />}
            {isReportProcessing ? "생성 중" : hasReport ? "다시 만들기" : "회의록 만들기"}
          </button>
          <ToolbarLink href={reportArtifactUrls?.downloadHref} primary>
            <FileDown size={16} />
            PDF 다운로드
          </ToolbarLink>
          <button
            className="caps-minutes-toolbar-button"
            disabled={!visibleLatestReport?.id || isReportProcessing || editLoading || editSaving}
            onClick={handleOpenEditor}
            type="button"
          >
            {editLoading ? <Loader className="spinner" size={16} /> : <Pencil size={16} />}
            편집
          </button>
        </div>
      </div>

      {actionError ? <div className="caps-inline-alert caps-minutes-feedback">{actionError}</div> : null}
      {actionNotice ? (
        <div className="caps-inline-notice caps-minutes-feedback">{actionNotice}</div>
      ) : null}

      <div className="caps-minutes-page-shell">
        {pdfPreviewHref ? (
          <>
            <iframe
              className="caps-minutes-pdf-frame"
              loading="lazy"
              src={pdfPreviewHref}
              title="회의록 PDF 문서"
            />
            {isReportProcessing ? (
              <div className="caps-minutes-generation-badge">
                <Loader className="spinner" size={14} />
                새 버전 생성 중
              </div>
            ) : null}
          </>
        ) : isReportProcessing ? (
          <div className="caps-minutes-processing-state">
            <Loader className="spinner" size={24} />
            <strong>회의록을 만드는 중입니다.</strong>
            <p>생성이 끝나면 PDF 문서가 이 화면에 표시됩니다.</p>
          </div>
        ) : (
        <article className="caps-minutes-page" aria-label="회의록 문서">
          <header className="caps-minutes-doc-header">
            <h1>회의록</h1>
          </header>

          <table className="caps-minutes-meta-table">
            <tbody>
              <tr>
                <th>회의 제목</th>
                <td colSpan="3">{session?.title || "제목 없는 회의"}</td>
              </tr>
              <tr>
                <th>일시</th>
                <td>{formatDateTime(session?.started_at)}</td>
                <th>소요 시간</th>
                <td>{meta.duration}</td>
              </tr>
              <tr>
                <th>참석자</th>
                <td colSpan="3">{meta.participants}</td>
              </tr>
              <tr>
                <th>소스</th>
                <td>{sourceLabel}</td>
                <th>발화자 수</th>
                <td>{meta.participantsCount}</td>
              </tr>
              <tr>
                <th>안건</th>
                <td colSpan="3">{agenda}</td>
              </tr>
            </tbody>
          </table>

          <MinutesSection title="1. 회의개요">
            <div className="caps-minutes-content-box compact">
              <MinutesList emptyText="회의 개요가 아직 없습니다." items={recap.overviewLines} />
            </div>
          </MinutesSection>

          <MinutesSection title="2. 회의내용">
            <div className="caps-minutes-content-box">
              {recap.topics.length > 0 ? (
                recap.topics.map((topic, index) => (
                  <TopicBlock index={index} key={`${topic.title}-${index}`} topic={topic} />
                ))
              ) : (
                <EmptyLine>회의록 분석이 완료되면 회의내용이 표시됩니다.</EmptyLine>
              )}
            </div>
          </MinutesSection>

          <MinutesSection title="3. 결정사항">
            <div className="caps-minutes-content-box compact">
              <MinutesList
                emptyText="아직 확정된 결정사항이 없습니다."
                items={recap.decisions.slice(0, 8)}
                ordered
              />
            </div>
          </MinutesSection>

          <MinutesSection title="4. 후속 조치">
            <div className="caps-minutes-content-box compact">
              <ActionList actions={recap.actions} />
            </div>
          </MinutesSection>

          <MinutesSection title="5. 참고 대화록">
            <div className="caps-minutes-content-box transcript">
              <TranscriptExcerpt segments={transcriptSegments} />
            </div>
          </MinutesSection>
        </article>
        )}
      </div>

      {editorOpen ? (
        <>
          <button
            aria-label="회의록 편집 닫기"
            className="caps-minutes-editor-backdrop"
            onClick={() => setEditorOpen(false)}
            type="button"
          />
          <ReportEditorPanel
            document={editDraft}
            error={editError}
            loading={editLoading}
            onChange={setEditDraft}
            onClose={() => setEditorOpen(false)}
            onSave={handleSaveEditor}
            saving={editSaving}
          />
        </>
      ) : null}
    </div>
  );
}
