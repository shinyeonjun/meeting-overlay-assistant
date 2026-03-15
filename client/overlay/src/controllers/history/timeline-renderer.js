import { elements } from "../../dom/elements.js";
import { getSelectedMeetingContextSummary } from "../context-controller.js";
import { appState } from "../../state/app-state.js";
import { buildEmptyState, TIMELINE_LIMIT } from "./helpers.js";
import {
    formatDateTime,
    formatDistance,
    formatInsightSourceLabel,
    formatReportTypeLabel,
    formatSourceLabel,
    formatStatusLabel,
    formatUpdatedAt,
    getTimelineContextLabel,
} from "./formatters.js";

export function renderHistoryTimelinePanel() {
    if (
        !elements.historyTimelinePanel
        || !elements.historyTimelineTitle
        || !elements.historyTimelineMeta
        || !elements.historyTimelineList
    ) {
        return;
    }

    const contextSummary = getSelectedMeetingContextSummary();
    if (!contextSummary.hasSelection) {
        elements.historyTimelinePanel.classList.add("hidden");
        return;
    }

    elements.historyTimelinePanel.classList.remove("hidden");
    elements.historyTimelineTitle.textContent = getTimelineContextLabel(contextSummary);
    elements.historyTimelineMeta.textContent = [
        `회의 ${appState.history.timeline.sessionCount}건`,
        `리포트 ${appState.history.timeline.reportCount}건`,
    ].join(" / ");

    elements.historyTimelineList.replaceChildren();

    if (appState.history.timelineLoading) {
        elements.historyTimelineList.append(buildEmptyState("선택한 맥락의 최근 기록을 불러오는 중입니다."));
        return;
    }

    const items = buildTimelineEntries();
    if (!items.length) {
        elements.historyTimelineList.append(buildEmptyState("이 맥락으로 연결된 최근 회의가 아직 없습니다."));
        return;
    }

    for (const item of items) {
        const button = document.createElement("button");
        button.type = "button";
        button.className = "history-list-item history-timeline-item";
        button.dataset.historyKind = item.kind;
        button.dataset.historyId = item.id;

        if (appState.history.selectedKind === item.kind && appState.history.selectedId === item.id) {
            button.classList.add("active");
        }

        const title = document.createElement("span");
        title.className = "history-item-title";
        title.textContent = item.title;

        const meta = document.createElement("span");
        meta.className = "history-item-meta";
        meta.textContent = item.meta;

        button.append(title, meta);
        elements.historyTimelineList.append(button);
    }
}

export function renderCarryOverPanel() {
    if (
        !elements.historyCarryOverPanel
        || !elements.historyCarryOverDecisionList
        || !elements.historyCarryOverActionList
        || !elements.historyCarryOverRiskList
        || !elements.historyCarryOverQuestionList
    ) {
        return;
    }

    const contextSummary = getSelectedMeetingContextSummary();
    if (!contextSummary.hasSelection) {
        elements.historyCarryOverPanel.classList.add("hidden");
        return;
    }

    elements.historyCarryOverPanel.classList.remove("hidden");
    renderCarryOverGroup(
        elements.historyCarryOverDecisionList,
        appState.history.timeline.carryOver.decisions,
        "이어볼 결정 사항이 없습니다.",
    );
    renderCarryOverGroup(
        elements.historyCarryOverActionList,
        appState.history.timeline.carryOver.actionItems,
        "이어갈 액션 아이템이 없습니다.",
    );
    renderCarryOverGroup(
        elements.historyCarryOverRiskList,
        appState.history.timeline.carryOver.risks,
        "기록된 리스크가 없습니다.",
    );
    renderCarryOverGroup(
        elements.historyCarryOverQuestionList,
        appState.history.timeline.carryOver.questions,
        "남아 있는 질문이 없습니다.",
    );
}

export function renderRetrievalBriefPanel() {
    if (
        !elements.historyRetrievalPanel
        || !elements.historyRetrievalMeta
        || !elements.historyRetrievalList
    ) {
        return;
    }

    const contextSummary = getSelectedMeetingContextSummary();
    if (!contextSummary.hasSelection) {
        elements.historyRetrievalPanel.classList.add("hidden");
        return;
    }

    elements.historyRetrievalPanel.classList.remove("hidden");
    elements.historyRetrievalList.replaceChildren();

    if (appState.history.timelineLoading) {
        elements.historyRetrievalMeta.textContent = "관련 문서를 찾는 중입니다.";
        elements.historyRetrievalList.append(buildEmptyState("관련 과거 문서를 찾는 중입니다."));
        return;
    }

    const brief = appState.history.timeline.retrievalBrief;
    elements.historyRetrievalMeta.textContent = brief.query
        ? `질의 "${brief.query}" / ${brief.resultCount}건`
        : "검색 질의 없음";

    if (!brief.items.length) {
        elements.historyRetrievalList.append(buildEmptyState("이 맥락으로 연결된 관련 문서를 아직 찾지 못했습니다."));
        return;
    }

    for (const item of brief.items) {
        const card = document.createElement("div");
        card.className = "history-carry-over-item";

        const title = document.createElement("span");
        title.className = "history-item-title";
        title.textContent = item.chunkHeading || item.documentTitle;

        const body = document.createElement("span");
        body.className = "history-item-meta";
        body.textContent = item.chunkText;

        const meta = document.createElement("span");
        meta.className = "history-item-meta";
        meta.textContent = [
            formatReportTypeLabel(item.sourceType),
            item.documentTitle,
            `거리 ${formatDistance(item.distance)}`,
        ].filter(Boolean).join(" / ");

        card.append(title, body, meta);
        elements.historyRetrievalList.append(card);
    }
}

function renderCarryOverGroup(container, items, emptyText) {
    if (!container) {
        return;
    }

    container.replaceChildren();

    if (appState.history.timelineLoading) {
        container.append(buildEmptyState("이어보기 메모를 불러오는 중입니다."));
        return;
    }

    if (!items.length) {
        container.append(buildEmptyState(emptyText));
        return;
    }

    for (const item of items) {
        const card = document.createElement("div");
        card.className = "history-carry-over-item";

        const title = document.createElement("span");
        title.className = "history-item-title";
        title.textContent = item.title;

        const meta = document.createElement("span");
        meta.className = "history-item-meta";
        meta.textContent = [
            item.sessionTitle,
            formatStatusLabel(item.state),
            formatUpdatedAt(item.updatedAtMs),
        ].filter(Boolean).join(" / ");

        card.append(title, meta);
        container.append(card);
    }
}

function buildTimelineEntries() {
    const sessionItems = appState.history.timeline.sessions.map((item) => ({
        kind: "session",
        id: item.id,
        title: item.title || "제목 없는 회의",
        meta: [
            "회의",
            formatStatusLabel(item.status),
            formatSourceLabel(item.primaryInputSource),
            formatDateTime(item.startedAt),
        ].join(" / "),
        sortKey: Date.parse(item.startedAt) || 0,
    }));

    const reportItems = appState.history.timeline.reports.map((item) => ({
        kind: "report",
        id: item.id,
        title: `${formatReportTypeLabel(item.reportType)} / v${item.version}`,
        meta: [
            "리포트",
            formatInsightSourceLabel(item.insightSource),
            formatDateTime(item.generatedAt),
        ].join(" / "),
        sortKey: Date.parse(item.generatedAt) || 0,
    }));

    return [...reportItems, ...sessionItems]
        .sort((left, right) => right.sortKey - left.sortKey)
        .slice(0, TIMELINE_LIMIT);
}
