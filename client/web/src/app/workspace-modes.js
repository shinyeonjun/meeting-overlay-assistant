export const WORKSPACE_MODES = {
  home: "home",
  meetings: "meetings",
  assistant: "assistant",
};

export const WORKSPACE_MODE_COPY = {
  [WORKSPACE_MODES.home]: {
    title: "오늘 할 일",
    description: "진행 중인 회의와 확인이 필요한 작업을 먼저 보여줍니다.",
  },
  [WORKSPACE_MODES.meetings]: {
    title: "회의",
    description: "전사, 노트, 요약을 확인하고 회의록 산출물로 이동합니다.",
  },
  [WORKSPACE_MODES.assistant]: {
    title: "챗봇",
    description: "회의 내용을 질문하고 관련 근거를 확인합니다.",
  },
};

const WORKSPACE_LOAD_OPTIONS = {
  [WORKSPACE_MODES.home]: {
    scope: "all",
    limit: 16,
    includeReports: true,
    includeCarryOver: true,
    includeRetrievalBrief: false,
  },
  [WORKSPACE_MODES.meetings]: {
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
  return WORKSPACE_LOAD_OPTIONS[mode] ?? WORKSPACE_LOAD_OPTIONS[WORKSPACE_MODES.home];
}
