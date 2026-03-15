function normalizeReportListItem(item) {
    return {
        id: item.id,
        sessionId: item.session_id,
        reportType: item.report_type,
        version: item.version,
        filePath: item.file_path,
        insightSource: item.insight_source,
        generatedByUserId: item.generated_by_user_id ?? null,
        generatedAt: item.generated_at,
    };
}

function normalizeReportShareItem(item) {
    return {
        id: item.id,
        reportId: item.report_id,
        sharedByUserId: item.shared_by_user_id,
        sharedByLoginId: item.shared_by_login_id,
        sharedByDisplayName: item.shared_by_display_name,
        sharedWithUserId: item.shared_with_user_id,
        sharedWithLoginId: item.shared_with_login_id,
        sharedWithDisplayName: item.shared_with_display_name,
        permission: item.permission,
        note: item.note ?? "",
        createdAt: item.created_at,
    };
}

function normalizeSharedReportItem(item) {
    return {
        shareId: item.share_id,
        reportId: item.report_id,
        sessionId: item.session_id,
        reportType: item.report_type,
        version: item.version,
        filePath: item.file_path,
        fileName: item.file_name ?? "",
        insightSource: item.insight_source,
        generatedByUserId: item.generated_by_user_id ?? null,
        generatedAt: item.generated_at,
        sharedByUserId: item.shared_by_user_id,
        sharedByLoginId: item.shared_by_login_id,
        sharedByDisplayName: item.shared_by_display_name,
        permission: item.permission,
        note: item.note ?? "",
        sharedAt: item.shared_at,
    };
}

export function normalizeRegenerateReportsPayload(payload) {
    return {
        sessionId: payload.session_id,
        items: (payload.items ?? []).map((item) => ({
            id: item.id,
            reportType: item.report_type,
            version: item.version ?? null,
            filePath: item.file_path,
        })),
    };
}

export function normalizeFinalReportStatusPayload(payload) {
    return {
        sessionId: payload.session_id,
        status: payload.status,
        reportCount: payload.report_count ?? 0,
        latestReportId: payload.latest_report_id ?? null,
        latestReportType: payload.latest_report_type ?? null,
        latestGeneratedAt: payload.latest_generated_at ?? null,
        latestFilePath: payload.latest_file_path ?? null,
    };
}

export function normalizeReportListPayload(payload) {
    return (payload.items ?? []).map(normalizeReportListItem);
}

export function normalizeReportDetailPayload(payload) {
    return {
        ...normalizeReportListItem(payload),
        content: payload.content ?? null,
    };
}

export function normalizeReportShareListPayload(payload) {
    return (payload.items ?? []).map(normalizeReportShareItem);
}

export function normalizeReportSharePayload(payload) {
    return normalizeReportShareItem(payload);
}

export function normalizeSharedReportListPayload(payload) {
    return (payload.items ?? []).map(normalizeSharedReportItem);
}
