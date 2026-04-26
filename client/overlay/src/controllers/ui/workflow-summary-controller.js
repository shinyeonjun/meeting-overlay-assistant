import { appState } from "../../state/app-state.js";
import { setStatus } from "../ui-controller.js";

let workflowSummaryInitialized = false;

function getWorkflowElements() {
    return {
        panel: document.querySelector("#workflow-summary-panel"),
        overallBadge: document.querySelector("#workflow-overall-badge"),
        nextTitle: document.querySelector("#workflow-next-title"),
        nextCopy: document.querySelector("#workflow-next-copy"),
    };
}

export function setupWorkflowSummary() {
    if (workflowSummaryInitialized) {
        return;
    }

    const elements = getWorkflowElements();
    if (!elements.panel) {
        return;
    }

    workflowSummaryInitialized = true;
}

export function renderWorkflowSummary() {
    const elements = getWorkflowElements();
    if (!elements.panel) {
        return;
    }

    const nextStep = buildNextStep();
    const overallStatus = buildOverallStatus();

    if (elements.nextTitle) {
        elements.nextTitle.textContent = nextStep.title;
    }
    if (elements.nextCopy) {
        elements.nextCopy.textContent = nextStep.copy;
    }
    if (elements.overallBadge) {
        setStatus(elements.overallBadge, overallStatus.label, overallStatus.tone);
    }
}

function buildOverallStatus() {
    if (!appState.auth.initialized) {
        return { label: "확인 중", tone: "idle" };
    }

    if (appState.auth.authEnabled && !appState.auth.user) {
        return {
            label: appState.auth.bootstrapRequired ? "초기 설정 필요" : "로그인 필요",
            tone: appState.auth.bootstrapRequired ? "error" : "idle",
        };
    }

    if (!appState.session.id) {
        return {
            label: appState.runtime.startReady ? "시작 준비" : "준비 중",
            tone: appState.runtime.startReady ? "live" : "idle",
        };
    }

    if (appState.session.status === "running") {
        return { label: "회의 진행 중", tone: "live" };
    }

    if (appState.session.status === "ending") {
        return { label: "종료 처리 중", tone: "idle" };
    }

    if (appState.session.status === "ended") {
        if (appState.report.status === "failed") {
            return { label: "리포트 확인 필요", tone: "error" };
        }
        if (appState.report.status === "completed" || appState.report.status === "ready") {
            return { label: "리포트 준비 완료", tone: "live" };
        }
        return { label: "리포트 대기", tone: "idle" };
    }

    return { label: "세션 준비", tone: "idle" };
}

function buildNextStep() {
    if (!appState.auth.initialized) {
        return {
            title: "서버와 인증 상태를 확인하는 중입니다.",
            copy: "Control 서버와 로그인 상태가 정리되면 바로 회의를 시작할 수 있습니다.",
        };
    }

    if (appState.auth.authEnabled && appState.auth.bootstrapRequired) {
        return {
            title: "먼저 관리자 계정을 초기화해야 합니다.",
            copy: "관리자 계정을 만든 뒤 다시 로그인하면 회의 준비를 이어갈 수 있습니다.",
        };
    }

    if (appState.auth.authEnabled && !appState.auth.user) {
        return {
            title: "먼저 로그인해 주세요.",
            copy: "로그인하면 세션 생성, 실시간 자막, 웹 워크스페이스 handoff까지 바로 이어집니다.",
        };
    }

    if (!appState.session.id) {
        return {
            title: "세션 제목과 입력 소스를 정한 뒤 초안을 만드세요.",
            copy: appState.runtime.startReady
                ? "입력 장치와 STT 준비가 끝났습니다. 세션만 만들면 바로 회의를 시작할 수 있습니다."
                : "아직 런타임 준비 중입니다. 세션 초안은 먼저 만들어 둘 수 있습니다.",
        };
    }

    if (appState.session.status === "draft") {
        return {
            title: appState.runtime.startReady
                ? "회의를 시작할 준비가 됐습니다."
                : "회의 시작 전에 장치 준비 상태를 확인해 주세요.",
            copy: appState.runtime.startReady
                ? "시작 버튼을 누르면 실시간 자막 수집이 시작됩니다. 질문과 결정은 회의 후 리포트에서 확인합니다."
                : "bridge, 서버, 선택한 소스가 모두 준비되면 시작 버튼이 활성화됩니다.",
        };
    }

    if (appState.session.status === "running") {
        return {
            title: "오버레이에서는 지금 흐름만 집중해서 보시면 됩니다.",
            copy: appState.session.currentTopic
                ? `현재 주제는 "${appState.session.currentTopic}" 입니다. 실시간 자막만 확인하면 됩니다.`
                : "실시간 자막만 확인하고, 질문/결정/액션 정리는 회의 후 리포트에서 이어갑니다.",
        };
    }

    if (appState.report.status === "failed") {
        return {
            title: "리포트 상태를 웹에서 확인해 주세요.",
            copy: "오버레이는 상태만 보여주고, 재시도와 상세 검토는 웹 워크스페이스에서 처리합니다.",
        };
    }

    if (appState.report.status === "completed" || appState.report.status === "ready") {
        return {
            title: "리포트가 준비되었습니다.",
            copy: "이제 웹 워크스페이스에서 리포트 검토, 기록 확인, assistant 검색으로 이어가면 됩니다.",
        };
    }

    return {
        title: "회의가 끝났습니다. 웹에서 후속 작업을 이어가세요.",
        copy: "리포트 생성 상태, 기록, assistant 검색은 웹 워크스페이스에서 처리하는 흐름으로 정리되어 있습니다.",
    };
}
