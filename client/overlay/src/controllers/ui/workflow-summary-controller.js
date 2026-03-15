import { appState } from "../../state/app-state.js";
import { activateTab, openWorkspace, setStatus } from "../ui-controller.js";

let workflowEventsBound = false;

function getWorkflowElements() {
    return {
        panel: document.querySelector("#workflow-summary-panel"),
        nextTitle: document.querySelector("#workflow-next-title"),
        nextCopy: document.querySelector("#workflow-next-copy"),
        authCard: document.querySelector("#workflow-auth-card"),
        authTitle: document.querySelector("#workflow-auth-title"),
        authBadge: document.querySelector("#workflow-auth-badge"),
        authMeta: document.querySelector("#workflow-auth-meta"),
        sessionCard: document.querySelector("#workflow-session-card"),
        sessionTitle: document.querySelector("#workflow-session-title"),
        sessionBadge: document.querySelector("#workflow-session-badge"),
        sessionMeta: document.querySelector("#workflow-session-meta"),
        reportCard: document.querySelector("#workflow-report-card"),
        reportTitle: document.querySelector("#workflow-report-title"),
        reportBadge: document.querySelector("#workflow-report-badge"),
        reportMeta: document.querySelector("#workflow-report-meta"),
        historyCard: document.querySelector("#workflow-history-card"),
        historyTitle: document.querySelector("#workflow-history-title"),
        historyBadge: document.querySelector("#workflow-history-badge"),
        historyMeta: document.querySelector("#workflow-history-meta"),
        cards: Array.from(document.querySelectorAll("[data-workflow-target]")),
    };
}

export function setupWorkflowSummary() {
    if (workflowEventsBound) {
        return;
    }

    const elements = getWorkflowElements();
    if (!elements.panel) {
        return;
    }

    for (const card of elements.cards) {
        card.addEventListener("click", () => {
            const target = card.dataset.workflowTarget;
            if (!target) {
                return;
            }
            openWorkspace();
            activateTab(target);
            renderWorkflowSummary();
        });
    }

    workflowEventsBound = true;
}

export function renderWorkflowSummary() {
    const elements = getWorkflowElements();
    if (!elements.panel) {
        return;
    }

    const authCard = buildAuthCard();
    const sessionCard = buildSessionCard();
    const reportCard = buildReportCard();
    const historyCard = buildHistoryCard();
    const nextStep = buildNextStep();

    applyCard(elements.authCard, elements.authTitle, elements.authBadge, elements.authMeta, authCard);
    applyCard(elements.sessionCard, elements.sessionTitle, elements.sessionBadge, elements.sessionMeta, sessionCard);
    applyCard(elements.reportCard, elements.reportTitle, elements.reportBadge, elements.reportMeta, reportCard);
    applyCard(elements.historyCard, elements.historyTitle, elements.historyBadge, elements.historyMeta, historyCard);

    if (elements.nextTitle) {
        elements.nextTitle.textContent = nextStep.title;
    }
    if (elements.nextCopy) {
        elements.nextCopy.textContent = nextStep.copy;
    }

    const currentTab = document.querySelector(".workspace-tab.active")?.dataset.tab ?? null;
    for (const card of elements.cards) {
        card.classList.toggle("is-current", card.dataset.workflowTarget === currentTab);
    }
}

function applyCard(cardElement, titleElement, badgeElement, metaElement, card) {
    if (!cardElement || !titleElement || !badgeElement || !metaElement) {
        return;
    }

    titleElement.textContent = card.title;
    metaElement.textContent = card.meta;
    setStatus(badgeElement, card.badgeText, card.badgeTone);
    cardElement.dataset.tone = card.cardTone ?? card.badgeTone;
}

function buildAuthCard() {
    if (!appState.auth.initialized) {
        return {
            title: "인증 확인",
            meta: "서버와 로그인 상태를 확인하고 있습니다.",
            badgeText: "checking",
            badgeTone: "idle",
        };
    }

    if (!appState.auth.authEnabled) {
        return {
            title: "인증 없이 사용",
            meta: "이 서버는 로그인 없이 바로 사용할 수 있습니다.",
            badgeText: "open",
            badgeTone: "live",
        };
    }

    if (appState.auth.bootstrapRequired) {
        return {
            title: "관리자 초기화 필요",
            meta: "첫 관리자 계정을 만든 뒤 로그인할 수 있습니다.",
            badgeText: "setup",
            badgeTone: "error",
        };
    }

    if (appState.auth.user) {
        const workspaceBits = [
            appState.auth.user.login_id,
            appState.auth.user.workspace_name,
        ].filter(Boolean);

        return {
            title: appState.auth.user.display_name || appState.auth.user.login_id,
            meta: workspaceBits.join(" · ") || "로그인된 사용자입니다.",
            badgeText: appState.auth.user.workspace_role || "member",
            badgeTone: "live",
        };
    }

    return {
        title: "로그인 필요",
        meta: "접속 후 회의, 공유, 히스토리 기능을 사용할 수 있습니다.",
        badgeText: "login",
        badgeTone: "idle",
    };
}

function buildSessionCard() {
    const participants = appState.session.participants.length;
    const source = formatInputSource(
        appState.session.primaryInputSource
        || appState.runtime.selectedSource
        || document.querySelector("#session-source")?.value
        || null,
    );

    if (!appState.session.id) {
        return {
            title: "세션 준비",
            meta: `${source} · 제목과 입력 소스를 정해 초안을 만듭니다.`,
            badgeText: appState.runtime.startReady ? "ready" : "idle",
            badgeTone: appState.runtime.startReady ? "ready" : "idle",
        };
    }

    if (appState.session.status === "draft") {
        return {
            title: appState.session.title || "세션 초안",
            meta: `${source} · 참여자 ${participants}명 · ${appState.runtime.startReady ? "지금 시작할 수 있습니다." : "클라이언트와 STT 준비를 기다립니다."}`,
            badgeText: appState.runtime.startReady ? "ready" : "wait",
            badgeTone: appState.runtime.startReady ? "ready" : "idle",
        };
    }

    if (appState.session.status === "running") {
        return {
            title: appState.session.currentTopic || "회의 진행 중",
            meta: `${formatActiveSources(appState.session.actualActiveSources)} · 참여자 ${participants}명`,
            badgeText: "live",
            badgeTone: "live",
        };
    }

    return {
        title: appState.session.title || "회의 종료",
        meta: `${source} · 종료 후 리포트와 히스토리를 확인합니다.`,
        badgeText: "done",
        badgeTone: "idle",
    };
}

function buildReportCard() {
    const reportReady = isReportReady();

    if (!appState.session.id) {
        return {
            title: "리포트 대기",
            meta: "회의가 끝나면 markdown 또는 PDF로 정리합니다.",
            badgeText: "idle",
            badgeTone: "idle",
        };
    }

    if (appState.report.status === "failed") {
        return {
            title: "리포트 생성 실패",
            meta: "정리 탭에서 다시 생성하거나 상태를 확인해야 합니다.",
            badgeText: "failed",
            badgeTone: "error",
        };
    }

    if (reportReady) {
        return {
            title: "리포트 준비됨",
            meta: [
                appState.report.latestVersion ? `v${appState.report.latestVersion}` : null,
                appState.report.latestPath ? extractFileName(appState.report.latestPath) : "파일이 준비되었습니다.",
            ].filter(Boolean).join(" · "),
            badgeText: "ready",
            badgeTone: "live",
        };
    }

    if (appState.session.status === "ended") {
        return {
            title: "리포트 생성 대기",
            meta: "회의가 끝났습니다. 정리 탭에서 생성 상태를 확인하세요.",
            badgeText: appState.report.status === "processing" ? "processing" : "pending",
            badgeTone: "idle",
        };
    }

    return {
        title: "리포트 대기",
        meta: "회의 종료 전까지는 상태만 준비합니다.",
        badgeText: "idle",
        badgeTone: "idle",
    };
}

function buildHistoryCard() {
    const retrievalCount = appState.history.timeline.retrievalBrief.resultCount ?? 0;
    const sessionCount = appState.history.sessions.length;
    const reportCount = appState.history.reports.length;
    const sharedCount = appState.history.sharedReports.length;

    if (appState.history.loading || appState.history.timelineLoading) {
        return {
            title: "기록 불러오는 중",
            meta: "최근 세션, 리포트, 관련 문서를 갱신하고 있습니다.",
            badgeText: "sync",
            badgeTone: "idle",
        };
    }

    if (retrievalCount > 0) {
        return {
            title: `관련 문서 ${retrievalCount}건`,
            meta: appState.history.timeline.retrievalBrief.query
                ? `질의 "${appState.history.timeline.retrievalBrief.query}" 기준으로 이어볼 문서를 찾았습니다.`
                : "과거 문서를 이어서 볼 수 있습니다.",
            badgeText: "brief",
            badgeTone: "live",
        };
    }

    if (sessionCount || reportCount || sharedCount) {
        return {
            title: "기록 확인 가능",
            meta: `세션 ${sessionCount}건 · 리포트 ${reportCount}건${sharedCount ? ` · 공유 ${sharedCount}건` : ""}`,
            badgeText: "ready",
            badgeTone: "ready",
        };
    }

    return {
        title: "히스토리 비어 있음",
        meta: "세션과 리포트가 쌓이면 이어보기와 관련 문서가 여기에 모입니다.",
        badgeText: "idle",
        badgeTone: "idle",
    };
}

function buildNextStep() {
    if (!appState.auth.initialized) {
        return {
            title: "지금 상태를 확인하는 중입니다.",
            copy: "서버 연결과 인증 설정을 읽는 동안 잠깐만 기다리세요.",
        };
    }

    if (appState.auth.authEnabled && appState.auth.bootstrapRequired) {
        return {
            title: "먼저 관리자 계정을 초기화해야 합니다.",
            copy: "server-admin bootstrap-admin으로 첫 관리자를 만든 뒤 로그인 흐름을 시작하세요.",
        };
    }

    if (appState.auth.authEnabled && !appState.auth.user) {
        return {
            title: "먼저 로그인하세요.",
            copy: "로그인 후 세션 초안을 만들고 공유와 히스토리 기능까지 사용할 수 있습니다.",
        };
    }

    if (!appState.session.id) {
        return {
            title: "세션 제목과 입력 소스를 정해 초안을 만드세요.",
            copy: appState.runtime.startReady
                ? "클라이언트와 서버 준비는 끝났습니다. 회의 제목만 정하면 바로 시작할 수 있습니다."
                : "지금은 회의 초안을 만들고, 클라이언트와 STT 준비 상태를 함께 확인하면 됩니다.",
        };
    }

    if (appState.session.status === "draft") {
        return {
            title: appState.runtime.startReady
                ? "회의를 시작할 준비가 됐습니다."
                : "회의 시작 전 준비 상태를 확인하세요.",
            copy: appState.runtime.startReady
                ? "시작 버튼을 눌러 실시간 인사이트와 캡션을 켜면 됩니다."
                : "오디오 브리지와 STT가 준비되면 바로 시작할 수 있습니다.",
        };
    }

    if (appState.session.status === "running") {
        return {
            title: "회의 진행 중입니다.",
            copy: appState.session.currentTopic
                ? `현재 주제는 "${appState.session.currentTopic}" 입니다. 진행 탭에서 실시간 인사이트를 확인하세요.`
                : "진행 탭에서 실시간 발화와 인사이트를 보면서 회의를 이어가세요.",
        };
    }

    if (appState.report.status === "failed") {
        return {
            title: "리포트 생성 실패를 먼저 확인하세요.",
            copy: "정리 탭에서 다시 생성하거나 상태를 점검한 뒤 히스토리로 이어가면 됩니다.",
        };
    }

    if (!isReportReady()) {
        return {
            title: "정리 탭에서 리포트 상태를 확인하세요.",
            copy: "회의가 끝났습니다. transcript와 리포트 생성이 끝나면 기록 탭에서 바로 이어볼 수 있습니다.",
        };
    }

    if ((appState.history.timeline.retrievalBrief.resultCount ?? 0) > 0) {
        return {
            title: "관련 과거 문서까지 이어서 볼 수 있습니다.",
            copy: "기록 탭에서 세션, 리포트, retrieval brief를 함께 확인하고 다음 회의 준비까지 이어가세요.",
        };
    }

    return {
        title: "리포트가 준비됐습니다.",
        copy: "기록 탭에서 리포트를 공유하고 최근 세션과 이어보기 흐름을 확인하면 됩니다.",
    };
}

function isReportReady() {
    return appState.report.status === "ready" || appState.report.status === "completed";
}

function formatInputSource(source) {
    const labels = {
        mic: "마이크",
        system_audio: "시스템 오디오",
        file: "파일",
    };
    return labels[source] || "입력 미선택";
}

function formatActiveSources(sources) {
    if (!sources?.length) {
        return "입력 감지 대기";
    }

    return sources.map(formatInputSource).join(", ");
}

function extractFileName(filePath) {
    return String(filePath).split(/[\\/]/).pop() || filePath;
}
