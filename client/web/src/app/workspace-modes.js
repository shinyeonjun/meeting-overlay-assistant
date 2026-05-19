export const WORKSPACE_MODES = {
  overview: "overview",
  notes: "notes",
  recaps: "recaps",
  assistant: "assistant",
  schedule: "schedule",
  home: "overview",
  meetings: "notes",
  live: "notes",
};

export const WORKSPACE_TOP_NAV_ITEMS = [
  { id: WORKSPACE_MODES.overview, label: "대시보드" },
  { id: WORKSPACE_MODES.notes, label: "노트" },
  { id: WORKSPACE_MODES.recaps, label: "회의록" },
  { id: WORKSPACE_MODES.assistant, label: "챗봇" },
  { id: WORKSPACE_MODES.schedule, label: "일정" },
];

export const WORKSPACE_MODE_COPY = {
  [WORKSPACE_MODES.overview]: {
    title: "대시보드",
    description: "오늘 확인해야 할 회의 흐름과 바로 할 일을 정리합니다.",
  },
  [WORKSPACE_MODES.notes]: {
    title: "노트",
    description: "회의를 선택해 노트, 전사 원문, 인사이트를 확인하고 다시 정리합니다.",
  },
  [WORKSPACE_MODES.recaps]: {
    title: "회의록",
    description: "회의를 선택해 공식 회의록을 만들고 편집하고 PDF로 내려받습니다.",
  },
  [WORKSPACE_MODES.assistant]: {
    title: "챗봇",
    description: "저장된 회의 자료에서 근거를 찾아 질문에 답합니다.",
  },
  [WORKSPACE_MODES.schedule]: {
    title: "일정",
    description: "예정된 회의와 다음 회의로 이어질 메모를 준비합니다.",
  },
};

const WORKSPACE_LOAD_OPTIONS = {
  [WORKSPACE_MODES.overview]: {
    scope: "all",
    limit: 16,
    includeReports: true,
    includeCarryOver: true,
    includeRetrievalBrief: false,
  },
  [WORKSPACE_MODES.notes]: {
    scope: "all",
    limit: 24,
    includeReports: true,
    includeCarryOver: false,
    includeRetrievalBrief: false,
  },
  [WORKSPACE_MODES.recaps]: {
    scope: "all",
    limit: 24,
    includeReports: true,
    includeCarryOver: false,
    includeRetrievalBrief: false,
  },
  [WORKSPACE_MODES.assistant]: {
    scope: "all",
    limit: 24,
    includeReports: true,
    includeCarryOver: false,
    includeRetrievalBrief: true,
  },
  [WORKSPACE_MODES.schedule]: {
    scope: "all",
    limit: 24,
    includeReports: true,
    includeCarryOver: true,
    includeRetrievalBrief: false,
  },
};

export function getWorkspaceLoadOptions(mode) {
  return WORKSPACE_LOAD_OPTIONS[mode] ?? WORKSPACE_LOAD_OPTIONS[WORKSPACE_MODES.overview];
}
