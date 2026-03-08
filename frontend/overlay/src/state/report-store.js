export function applyReport(state, reportPayload) {
    state.report.latestPath = reportPayload.filePath;
    state.report.latestReportId = reportPayload.id ?? null;
    state.report.latestReportType = reportPayload.reportType ?? null;
    state.report.latestVersion = reportPayload.version ?? null;
    state.report.generatedAt = reportPayload.generatedAt ?? null;
    state.report.content = reportPayload.content ?? "";
    state.report.speakerTranscript = reportPayload.speakerTranscript ?? [];
    state.report.speakerEvents = reportPayload.speakerEvents ?? [];
    state.report.status = "ready";
}

export function applyReportHistory(state, items) {
    state.report.history = items;
    if (!items.length) {
        return;
    }

    const latest = items[items.length - 1];
    state.report.latestReportId = latest.id ?? state.report.latestReportId;
    state.report.latestReportType = latest.reportType ?? state.report.latestReportType;
    state.report.latestVersion = latest.version ?? state.report.latestVersion;
    state.report.latestPath = latest.filePath ?? state.report.latestPath;
    state.report.generatedAt = latest.generatedAt ?? state.report.generatedAt;
}
