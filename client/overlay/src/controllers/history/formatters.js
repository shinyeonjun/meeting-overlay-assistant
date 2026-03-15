import { appState } from "../../state/app-state.js";

export function formatDateTime(value) {
    if (!value) {
        return "-";
    }

    const parsed = new Date(value);
    if (Number.isNaN(parsed.getTime())) {
        return value;
    }

    return parsed.toLocaleString("ko-KR", {
        month: "2-digit",
        day: "2-digit",
        hour: "2-digit",
        minute: "2-digit",
    });
}

export function formatUpdatedAt(value) {
    if (!value) {
        return "-";
    }
    return formatDateTime(new Date(value).toISOString());
}

export function formatDistance(value) {
    if (typeof value !== "number" || Number.isNaN(value)) {
        return "-";
    }
    return value.toFixed(3);
}

export function formatStatusLabel(value) {
    const labels = {
        draft: "준비됨",
        running: "진행 중",
        ended: "종료",
        archived: "보관",
        open: "열림",
        confirmed: "확정",
        candidate: "후보",
        answered: "답변됨",
        unresolved: "미해결",
        updated: "업데이트",
        monitoring: "관찰 중",
        resolved: "해결",
        closed: "종결",
        active: "활성",
    };
    return labels[value] ?? value ?? "-";
}

export function formatSourceLabel(value) {
    const labels = {
        mic_and_audio: "마이크 + 시스템 오디오",
        mic: "마이크",
        system_audio: "시스템 오디오",
        file: "오디오 파일",
    };
    return labels[value] ?? value ?? "-";
}

export function formatReportTypeLabel(value) {
    if (value === "report") {
        return "리포트";
    }
    if (value === "history_carry_over") {
        return "Carry-over";
    }
    if (value === "session_summary") {
        return "세션 요약";
    }
    if (value === "markdown") {
        return "Markdown 리포트";
    }
    if (value === "pdf") {
        return "PDF 리포트";
    }
    return value ? `${String(value).toUpperCase()} 리포트` : "리포트";
}

export function formatInsightSourceLabel(value) {
    if (value === "high_precision_audio") {
        return "고정밀 오디오 분석";
    }
    if (value === "live_fallback") {
        return "실시간 분석 기반";
    }
    return value || "-";
}

export function extractFileLabel(filePath) {
    if (!filePath) {
        return "파일 이름 확인 필요";
    }

    const parts = String(filePath).split(/[\\/]/);
    return parts[parts.length - 1] || filePath;
}

export function buildContextSummaryText(summary) {
    return [
        summary.accountLabel ? `회사 ${summary.accountLabel}` : null,
        summary.contactLabel ? `상대 ${summary.contactLabel}` : null,
        summary.threadLabel ? `스레드 ${summary.threadLabel}` : null,
    ].filter(Boolean).join(" / ");
}

export function getTimelineContextLabel(summary) {
    if (summary.threadLabel) {
        return `${summary.threadLabel} 스레드의 최근 기록`;
    }
    if (summary.contactLabel) {
        return `${summary.contactLabel} 관련 최근 기록`;
    }
    if (summary.accountLabel) {
        return `${summary.accountLabel} 관련 최근 기록`;
    }
    return "선택한 맥락의 최근 기록";
}

export function formatContextMeta(item) {
    const accountLabel = appState.context.accounts.find((candidate) => candidate.id === item.accountId)?.name;
    const contactLabel = appState.context.contacts.find((candidate) => candidate.id === item.contactId)?.name;
    const threadLabel = appState.context.threads.find((candidate) => candidate.id === item.contextThreadId)?.title;

    return [
        accountLabel ? `회사 ${accountLabel}` : null,
        contactLabel ? `상대 ${contactLabel}` : null,
        threadLabel ? `스레드 ${threadLabel}` : null,
    ].filter(Boolean).join(" / ");
}

export function buildSessionMeta(item) {
    return [
        formatContextMeta(item),
        formatStatusLabel(item.status),
        formatSourceLabel(item.primaryInputSource),
        formatDateTime(item.startedAt),
    ].filter(Boolean).join(" / ");
}

export function buildReportMeta(item) {
    return [
        formatContextMeta(item),
        formatReportTypeLabel(item.reportType),
        formatDateTime(item.generatedAt),
    ].filter(Boolean).join(" / ");
}

export function buildSharedReportMeta(item) {
    return [
        formatDateTime(item.sharedAt),
        item.note ? `메모 ${item.note}` : null,
    ].filter(Boolean).join(" / ");
}
