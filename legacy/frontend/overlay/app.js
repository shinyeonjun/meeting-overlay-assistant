const state = {
    sessionId: null,
    overviewTimerId: null,
    devTextSocket: null,
    latestReportPath: null,
};

const elements = {
    sessionTitle: document.querySelector("#session-title"),
    sessionSource: document.querySelector("#session-source"),
    createSessionButton: document.querySelector("#create-session-btn"),
    sessionId: document.querySelector("#session-id"),
    sessionStatus: document.querySelector("#session-status"),
    currentTopic: document.querySelector("#current-topic"),
    devTextInput: document.querySelector("#dev-text-input"),
    connectDevTextButton: document.querySelector("#connect-dev-text-btn"),
    sendDevTextButton: document.querySelector("#send-dev-text-btn"),
    devTextConnection: document.querySelector("#dev-text-connection"),
    questionCount: document.querySelector("#question-count"),
    decisionCount: document.querySelector("#decision-count"),
    actionCount: document.querySelector("#action-count"),
    riskCount: document.querySelector("#risk-count"),
    questionsList: document.querySelector("#questions-list"),
    decisionsList: document.querySelector("#decisions-list"),
    actionsList: document.querySelector("#actions-list"),
    risksList: document.querySelector("#risks-list"),
    reportStatus: document.querySelector("#report-status"),
    reportAudioPath: document.querySelector("#report-audio-path"),
    generateReportButton: document.querySelector("#generate-report-btn"),
    openReportButton: document.querySelector("#open-report-btn"),
    reportFilePath: document.querySelector("#report-file-path"),
    speakerTranscriptCount: document.querySelector("#speaker-transcript-count"),
    speakerEventCount: document.querySelector("#speaker-event-count"),
    speakerTranscriptList: document.querySelector("#speaker-transcript-list"),
    speakerEventsList: document.querySelector("#speaker-events-list"),
    eventCardTemplate: document.querySelector("#event-card-template"),
    speakerTranscriptTemplate: document.querySelector("#speaker-transcript-template"),
};

elements.createSessionButton.addEventListener("click", createSession);
elements.connectDevTextButton.addEventListener("click", connectDevTextSocket);
elements.sendDevTextButton.addEventListener("click", sendDevText);
elements.generateReportButton.addEventListener("click", generateReport);
elements.openReportButton.addEventListener("click", copyReportPath);

async function createSession() {
    const title = elements.sessionTitle.value.trim();
    const source = elements.sessionSource.value;
    if (!title) {
        window.alert("세션 제목을 입력하세요.");
        return;
    }

    setSessionStatus("세션 생성 중...", "idle");

    const response = await fetch("/api/v1/sessions", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
            title,
            mode: "meeting",
            source,
        }),
    });

    if (!response.ok) {
        setSessionStatus("세션 생성 실패", "error");
        window.alert("세션 생성에 실패했습니다.");
        return;
    }

    const payload = await response.json();
    state.sessionId = payload.id;
    elements.sessionId.textContent = payload.id;
    setSessionStatus(`${payload.source} 세션 실행 중`, "live");
    startOverviewPolling();
}

function startOverviewPolling() {
    stopOverviewPolling();
    refreshOverview();
    state.overviewTimerId = window.setInterval(refreshOverview, 1000);
}

function stopOverviewPolling() {
    if (state.overviewTimerId) {
        window.clearInterval(state.overviewTimerId);
        state.overviewTimerId = null;
    }
}

async function refreshOverview() {
    if (!state.sessionId) {
        return;
    }

    const response = await fetch(`/api/v1/sessions/${state.sessionId}/overview`);
    if (!response.ok) {
        setSessionStatus("overview 조회 실패", "error");
        return;
    }

    const payload = await response.json();
    elements.currentTopic.textContent = payload.current_topic ?? "아직 감지된 주제가 없습니다.";
    renderEventColumn(elements.questionsList, payload.questions, elements.questionCount);
    renderEventColumn(elements.decisionsList, payload.decisions, elements.decisionCount);
    renderEventColumn(elements.actionsList, payload.action_items, elements.actionCount);
    renderEventColumn(elements.risksList, payload.risks, elements.riskCount);
}

function renderEventColumn(container, items, countElement) {
    countElement.textContent = String(items.length);
    container.replaceChildren();

    if (!items.length) {
        container.append(buildEmptyCard("아직 이벤트가 없습니다."));
        return;
    }

    for (const item of items) {
        const fragment = elements.eventCardTemplate.content.cloneNode(true);
        const speakerElement = fragment.querySelector(".event-speaker");
        const titleElement = fragment.querySelector(".event-title");
        const stateElement = fragment.querySelector(".event-state");

        if (item.speaker_label) {
            speakerElement.textContent = item.speaker_label;
        } else {
            speakerElement.remove();
        }
        titleElement.textContent = item.title;
        stateElement.textContent = item.state;
        container.append(fragment);
    }
}

function connectDevTextSocket() {
    if (!state.sessionId) {
        window.alert("먼저 세션을 생성하세요.");
        return;
    }

    if (state.devTextSocket && state.devTextSocket.readyState === WebSocket.OPEN) {
        return;
    }

    const protocol = window.location.protocol === "https:" ? "wss" : "ws";
    const wsUrl = `${protocol}://${window.location.host}/api/v1/ws/dev-text/${state.sessionId}`;
    const socket = new WebSocket(wsUrl);

    socket.addEventListener("open", () => {
        state.devTextSocket = socket;
        setDevTextStatus("연결됨", "live");
    });

    socket.addEventListener("close", () => {
        if (state.devTextSocket === socket) {
            state.devTextSocket = null;
        }
        setDevTextStatus("종료", "idle");
    });

    socket.addEventListener("error", () => {
        setDevTextStatus("오류", "error");
    });

    socket.addEventListener("message", () => {
        refreshOverview();
    });
}

async function sendDevText() {
    const lines = elements.devTextInput.value
        .split(/\r?\n/)
        .map((line) => line.trim())
        .map((line) => line.replace(/^[-*]\s*/, ""))
        .filter(Boolean);

    if (!lines.length) {
        return;
    }

    if (!state.devTextSocket || state.devTextSocket.readyState !== WebSocket.OPEN) {
        connectDevTextSocket();
        window.setTimeout(sendDevText, 250);
        return;
    }

    for (const line of lines) {
        state.devTextSocket.send(line);
        await wait(180);
    }

    elements.devTextInput.value = "";
}

async function generateReport() {
    if (!state.sessionId) {
        window.alert("먼저 세션을 생성하세요.");
        return;
    }

    const audioPath = elements.reportAudioPath.value.trim();
    if (!audioPath) {
        window.alert("오디오 파일 경로를 입력하세요.");
        return;
    }

    setReportStatus("리포트 생성 중...", "idle");

    const response = await fetch(
        `/api/v1/reports/${state.sessionId}/markdown?audio_path=${encodeURIComponent(audioPath)}`,
        { method: "POST" },
    );

    if (!response.ok) {
        setReportStatus("리포트 생성 실패", "error");
        window.alert("리포트 생성에 실패했습니다.");
        return;
    }

    const payload = await response.json();
    state.latestReportPath = payload.file_path;
    elements.reportFilePath.textContent = payload.file_path;
    renderSpeakerTranscript(payload.speaker_transcript);
    renderSpeakerEvents(payload.speaker_events);
    setReportStatus("리포트 생성 완료", "live");
}

function renderSpeakerTranscript(items) {
    elements.speakerTranscriptCount.textContent = String(items.length);
    elements.speakerTranscriptList.replaceChildren();

    if (!items.length) {
        elements.speakerTranscriptList.append(buildEmptyCard("화자 전사 결과가 없습니다."));
        return;
    }

    for (const item of items) {
        const fragment = elements.speakerTranscriptTemplate.content.cloneNode(true);
        fragment.querySelector(".event-speaker").textContent = item.speaker_label;
        fragment.querySelector(".event-time").textContent = `${item.start_ms}ms - ${item.end_ms}ms`;
        fragment.querySelector(".event-state").textContent = `conf ${Number(item.confidence).toFixed(3)}`;
        fragment.querySelector(".event-body").textContent = item.text;
        elements.speakerTranscriptList.append(fragment);
    }
}

function renderSpeakerEvents(items) {
    elements.speakerEventCount.textContent = String(items.length);
    elements.speakerEventsList.replaceChildren();

    if (!items.length) {
        elements.speakerEventsList.append(buildEmptyCard("화자-이벤트 결과가 없습니다."));
        return;
    }

    for (const item of items) {
        const fragment = elements.eventCardTemplate.content.cloneNode(true);
        fragment.querySelector(".event-speaker").textContent = item.speaker_label;
        fragment.querySelector(".event-title").textContent = item.title;
        fragment.querySelector(".event-state").textContent = `${item.event_type} / ${item.state}`;
        elements.speakerEventsList.append(fragment);
    }
}

async function copyReportPath() {
    if (!state.latestReportPath) {
        window.alert("먼저 리포트를 생성하세요.");
        return;
    }

    await navigator.clipboard.writeText(state.latestReportPath);
    setReportStatus("파일 경로 복사됨", "live");
}

function setSessionStatus(text, tone) {
    elements.sessionStatus.textContent = text;
    elements.sessionStatus.className = `status-pill status-${tone}`;
}

function setDevTextStatus(text, tone) {
    elements.devTextConnection.textContent = text;
    elements.devTextConnection.className = `status-pill status-${tone}`;
}

function setReportStatus(text, tone) {
    elements.reportStatus.textContent = text;
    elements.reportStatus.className = `status-pill status-${tone}`;
}

function buildEmptyCard(text) {
    const empty = document.createElement("div");
    empty.className = "empty-card";
    empty.textContent = text;
    return empty;
}

function wait(milliseconds) {
    return new Promise((resolve) => window.setTimeout(resolve, milliseconds));
}

renderEventColumn(elements.questionsList, [], elements.questionCount);
renderEventColumn(elements.decisionsList, [], elements.decisionCount);
renderEventColumn(elements.actionsList, [], elements.actionCount);
renderEventColumn(elements.risksList, [], elements.riskCount);
renderSpeakerTranscript([]);
renderSpeakerEvents([]);
