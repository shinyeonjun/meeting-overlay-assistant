export const WORKSPACE_MODES = {
  overview: "overview",
  schedule: "schedule",
  live: "live",
  recaps: "recaps",
  assistant: "assistant",
  home: "overview",
  meetings: "recaps",
};

export const WORKSPACE_TOP_NAV_ITEMS = [
  { id: WORKSPACE_MODES.overview, label: "대시보드" },
  { id: WORKSPACE_MODES.schedule, label: "일정" },
  { id: WORKSPACE_MODES.live, label: "실시간" },
  { id: WORKSPACE_MODES.recaps, label: "회의록" },
  { id: WORKSPACE_MODES.assistant, label: "어시스턴트" },
];

export const WORKSPACE_MODE_COPY = {
  [WORKSPACE_MODES.overview]: {
    title: "회의 워크스페이스",
    description: "정리 중인 회의, 후속 작업, 최근 회의 결과를 한 번에 봅니다.",
  },
  [WORKSPACE_MODES.schedule]: {
    title: "일정",
    description: "오늘 확인할 회의와 다음 회의로 이어질 메모를 준비합니다.",
  },
  [WORKSPACE_MODES.live]: {
    title: "실시간 회의",
    description: "전사와 질문 감지를 보면서 회의를 진행합니다.",
  },
  [WORKSPACE_MODES.recaps]: {
    title: "회의 리캡",
    description: "정제된 회의록, 결정사항, 후속 작업, 산출물을 확인합니다.",
  },
  [WORKSPACE_MODES.assistant]: {
    title: "어시스턴트",
    description: "지난 회의의 결정, 질문, 다음 할 일을 회의 자료에서 찾습니다.",
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
  [WORKSPACE_MODES.schedule]: {
    scope: "all",
    limit: 24,
    includeReports: true,
    includeCarryOver: true,
    includeRetrievalBrief: false,
  },
  [WORKSPACE_MODES.live]: {
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
};

export function getWorkspaceLoadOptions(mode) {
  return WORKSPACE_LOAD_OPTIONS[mode] ?? WORKSPACE_LOAD_OPTIONS[WORKSPACE_MODES.overview];
}
