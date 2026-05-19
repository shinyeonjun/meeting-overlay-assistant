/** 회의록 편집 패널의 문서 변환 helper. */

export const EDITABLE_SECTION_GROUPS = [
  ["background", "논의 배경"],
  ["opinions", "주요 의견"],
  ["review", "검토 내용"],
  ["direction", "정리된 방향"],
];

export const TITLE_META_LABEL = "회의제목";

export const META_FIELD_LABELS = ["일시", "장소", "참석자"];

export function createEmptySection() {
  return {
    title: "새 소주제",
    background: [],
    opinions: [],
    review: [],
    direction: [],
  };
}

export function cloneEditableDocument(document) {
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

export function listItemsToText(items) {
  return (items ?? [])
    .map((item) => (typeof item === "string" ? item : item?.text || item?.task || ""))
    .filter(Boolean)
    .join("\n");
}

export function textToListItems(value) {
  return String(value ?? "")
    .split("\n")
    .map((line) => line.trim())
    .filter(Boolean)
    .map((text) => ({ text }));
}

export function actionItemsToText(items) {
  return (items ?? [])
    .map((item) => item?.task || item?.text || "")
    .filter(Boolean)
    .join("\n");
}

export function textToActionItems(value) {
  return String(value ?? "")
    .split("\n")
    .map((line) => line.trim())
    .filter(Boolean)
    .map((task) => ({ task }));
}

export function getMetaValue(document, label) {
  return (document?.metadata ?? []).find((item) => item?.label === label)?.value || "";
}

export function setMetaValue(document, label, value) {
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

export function appendSection(document) {
  return {
    ...document,
    sections: [...(document?.sections ?? []), createEmptySection()],
  };
}

export function removeSection(document, sectionIndex) {
  return {
    ...document,
    sections: (document?.sections ?? []).filter((_, index) => index !== sectionIndex),
  };
}

export function updateListField(document, field, value) {
  return {
    ...document,
    [field]: textToListItems(value),
  };
}

export function updateActionItemsField(document, value) {
  return {
    ...document,
    action_items: textToActionItems(value),
  };
}

export function updateSection(document, sectionIndex, updater) {
  const sections = [...(document?.sections ?? [])];
  const current = sections[sectionIndex] ?? { title: "" };
  sections[sectionIndex] = updater(current);
  return {
    ...document,
    sections,
  };
}
