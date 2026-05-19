import React, { useState } from "react";

import {
  appendSection,
  removeSection,
  setMetaValue,
  textToListItems,
  updateActionItemsField,
  updateListField,
  updateSection,
} from "./ReportEditorPanel.helpers.js";
import {
  EditorActions,
  EditorBody,
  EditorHeader,
  EditorLoadingPanel,
} from "./ReportEditorPanel.parts.jsx";

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
  const disabled = loading || saving;

  if (!document) {
    return <EditorLoadingPanel onClose={onClose} />;
  }

  function handleAddSection() {
    onChange(appendSection(document));
    setActiveSectionIndex(sections.length);
  }

  function handleDeleteSection() {
    onChange(removeSection(document, activeIndex));
    setActiveSectionIndex(Math.max(0, activeIndex - 1));
  }

  function handleUpdateSectionField(key, value) {
    onChange(
      updateSection(document, activeIndex, (current) => ({
        ...current,
        [key]: key === "title" ? value : textToListItems(value),
      })),
    );
  }

  return (
    <aside className="caps-minutes-editor-panel" aria-label="회의록 편집">
      <EditorHeader onClose={onClose} />
      {error ? <div className="caps-inline-alert">{error}</div> : null}
      <EditorBody
        activeIndex={activeIndex}
        activeSection={activeSection}
        disabled={disabled}
        document={document}
        onAddSection={handleAddSection}
        onDeleteSection={handleDeleteSection}
        onSelectSection={setActiveSectionIndex}
        onUpdateActionItems={(value) => onChange(updateActionItemsField(document, value))}
        onUpdateListField={(field, value) => onChange(updateListField(document, field, value))}
        onUpdateMeta={(label, value) => onChange(setMetaValue(document, label, value))}
        onUpdateSectionField={handleUpdateSectionField}
        sections={sections}
      />
      <EditorActions
        disabled={disabled}
        onClose={onClose}
        onSave={onSave}
        saving={saving}
      />
    </aside>
  );
}

export default ReportEditorPanel;
