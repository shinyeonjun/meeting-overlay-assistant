import React from "react";
import { Loader } from "lucide-react";

import {
  EDITABLE_SECTION_GROUPS,
  META_FIELD_LABELS,
  TITLE_META_LABEL,
  actionItemsToText,
  getMetaValue,
  listItemsToText,
} from "./ReportEditorPanel.helpers.js";

export function EditorHeader({ loading, onClose }) {
  return (
    <div className="caps-minutes-editor-header">
      <div>
        <strong>회의록 편집</strong>
        <p>
          {loading
            ? "편집 데이터를 불러오는 중입니다."
            : "저장하면 새 PDF 버전이 생성됩니다."}
        </p>
      </div>
      <button onClick={onClose} type="button">닫기</button>
    </div>
  );
}

export function EditorLoadingPanel({ onClose }) {
  return (
    <aside className="caps-minutes-editor-panel" aria-label="회의록 편집">
      <EditorHeader loading onClose={onClose} />
    </aside>
  );
}

export function EditorTextField({
  disabled,
  label,
  onChange,
  rows,
  value,
}) {
  const Control = rows ? "textarea" : "input";
  return (
    <label className="caps-editor-field">
      <span>{label}</span>
      <Control
        disabled={disabled}
        onChange={(event) => onChange(event.target.value)}
        rows={rows}
        value={value}
      />
    </label>
  );
}

export function MetadataFields({ disabled, document, onChange }) {
  return (
    <>
      <EditorTextField
        disabled={disabled}
        label="회의 제목"
        onChange={(value) => onChange(TITLE_META_LABEL, value)}
        value={getMetaValue(document, TITLE_META_LABEL)}
      />

      <div className="caps-editor-meta-grid">
        {META_FIELD_LABELS.map((label) => (
          <EditorTextField
            disabled={disabled}
            key={label}
            label={label}
            onChange={(value) => onChange(label, value)}
            value={getMetaValue(document, label)}
          />
        ))}
      </div>
    </>
  );
}

export function SectionNavigation({
  activeIndex,
  disabled,
  onAddSection,
  onSelectSection,
  sections,
}) {
  return (
    <nav className="caps-editor-section-nav" aria-label="소주제 목록">
      <div className="caps-editor-section-nav-head">
        <strong>회의내용</strong>
        <span>{sections.length}개</span>
      </div>
      {sections.map((section, sectionIndex) => (
        <button
          className={sectionIndex === activeIndex ? "active" : ""}
          key={`${section.title}-${sectionIndex}`}
          onClick={() => onSelectSection(sectionIndex)}
          type="button"
        >
          <span>소주제 {sectionIndex + 1}</span>
          <strong>{section.title || "제목 없음"}</strong>
        </button>
      ))}
      <button
        className="caps-editor-add-section"
        disabled={disabled}
        onClick={onAddSection}
        type="button"
      >
        소주제 추가
      </button>
    </nav>
  );
}

export function SectionEditorCard({
  activeIndex,
  activeSection,
  disabled,
  onDeleteSection,
  onUpdateSectionField,
  sections,
}) {
  if (!activeSection) {
    return <div className="caps-empty-panel compact">편집할 소주제가 없습니다.</div>;
  }

  return (
    <section className="caps-editor-section-card">
      <div className="caps-editor-section-title-row">
        <EditorTextField
          disabled={disabled}
          label={`소주제 ${activeIndex + 1}`}
          onChange={(value) => onUpdateSectionField("title", value)}
          value={activeSection.title || ""}
        />
        <button
          disabled={disabled || sections.length <= 1}
          onClick={onDeleteSection}
          type="button"
        >
          삭제
        </button>
      </div>

      {EDITABLE_SECTION_GROUPS.map(([key, label]) => (
        <EditorTextField
          disabled={disabled}
          key={key}
          label={label}
          onChange={(value) => onUpdateSectionField(key, value)}
          rows={6}
          value={listItemsToText(activeSection[key])}
        />
      ))}
    </section>
  );
}

export function EditorBody({
  activeIndex,
  activeSection,
  disabled,
  document,
  onAddSection,
  onDeleteSection,
  onSelectSection,
  onUpdateActionItems,
  onUpdateListField,
  onUpdateMeta,
  onUpdateSectionField,
  sections,
}) {
  return (
    <div className="caps-minutes-editor-body">
      <MetadataFields
        disabled={disabled}
        document={document}
        onChange={onUpdateMeta}
      />

      <EditorTextField
        disabled={disabled}
        label="안건"
        onChange={(value) => onUpdateListField("agenda", value)}
        rows={2}
        value={listItemsToText(document.agenda)}
      />

      <div className="caps-editor-section-workspace">
        <SectionNavigation
          activeIndex={activeIndex}
          disabled={disabled}
          onAddSection={onAddSection}
          onSelectSection={onSelectSection}
          sections={sections}
        />
        <SectionEditorCard
          activeIndex={activeIndex}
          activeSection={activeSection}
          disabled={disabled}
          onDeleteSection={onDeleteSection}
          onUpdateSectionField={onUpdateSectionField}
          sections={sections}
        />
      </div>

      <EditorTextField
        disabled={disabled}
        label="결정사항"
        onChange={(value) => onUpdateListField("decisions", value)}
        rows={4}
        value={listItemsToText(document.decisions)}
      />

      <EditorTextField
        disabled={disabled}
        label="향후일정"
        onChange={onUpdateActionItems}
        rows={4}
        value={actionItemsToText(document.action_items)}
      />

      <EditorTextField
        disabled={disabled}
        label="특이사항"
        onChange={(value) => onUpdateListField("risks", value)}
        rows={4}
        value={listItemsToText(document.risks)}
      />
    </div>
  );
}

export function EditorActions({ disabled, onClose, onSave, saving }) {
  return (
    <div className="caps-minutes-editor-actions">
      <button className="caps-minutes-toolbar-button" onClick={onClose} type="button">
        취소
      </button>
      <button
        className="caps-minutes-toolbar-button primary"
        disabled={disabled}
        onClick={onSave}
        type="button"
      >
        {saving ? <Loader className="spinner" size={16} /> : null}
        저장 후 PDF 생성
      </button>
    </div>
  );
}
