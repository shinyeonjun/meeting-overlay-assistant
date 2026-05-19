import { formatSourceLabel } from "../../../app/workspace-model.js";

function formatDuration(ms) {
  const totalSeconds = Math.max(0, Math.floor(Number(ms || 0) / 1000));
  if (!totalSeconds) {
    return "-";
  }
  const hours = Math.floor(totalSeconds / 3600);
  const minutes = Math.floor((totalSeconds % 3600) / 60);
  if (hours > 0) {
    return `${hours}시간 ${minutes}분`;
  }
  return `${minutes || 1}분`;
}

function formatTimestamp(ms) {
  const totalSeconds = Math.max(0, Math.floor(Number(ms || 0) / 1000));
  const minutes = String(Math.floor(totalSeconds / 60)).padStart(2, "0");
  const seconds = String(totalSeconds % 60).padStart(2, "0");
  return `${minutes}:${seconds}`;
}

function normalizeTextList(items, fallback = []) {
  const normalized = (items ?? [])
    .map((item) => {
      if (typeof item === "string") {
        return item;
      }
      return item?.title || item?.text || item?.task || item?.summary || "";
    })
    .map((item) => item.trim())
    .filter(Boolean);
  return normalized.length > 0 ? normalized : fallback;
}

function normalizeActionItems(summary, overview) {
  const source = summary?.next_actions?.length
    ? summary.next_actions
    : (overview?.action_items ?? []);
  return source.slice(0, 5).map((item, index) => ({
    id: item.id || item.event_id || `${item.title || item.task}-${index}`,
    title: item.title || item.task || "후속 작업",
    owner: item.owner || item.speaker_label || "담당 미정",
    dueDate: item.due_date || item.due || "",
  }));
}

function buildFallbackLine(visibleLatestReport) {
  return visibleLatestReport?.content
    ?.split("\n")
    .map((line) => line.replace(/^#+\s*/, "").trim())
    .find((line) => line.length > 20);
}

function buildRecapModel(overview, visibleLatestReport) {
  const summary = overview?.workspace_summary;
  const fallbackOverview = buildFallbackLine(visibleLatestReport);
  const overviewLines = normalizeTextList(
    summary?.summary,
    fallbackOverview ? [fallbackOverview] : [],
  );
  const topics = (summary?.topics ?? []).slice(0, 6).map((topic) => ({
    title: topic.title || "핵심 논의",
    summary: topic.summary || topic.direction || "",
    startMs: topic.start_ms,
    endMs: topic.end_ms,
  }));

  return {
    overviewLines:
      overviewLines.length > 0
        ? overviewLines
        : ["회의록이 생성되면 핵심 정리가 이곳에 표시됩니다."],
    topics,
    decisions: normalizeTextList(
      summary?.decisions,
      (overview?.decisions ?? []).map((item) => item.title),
    ),
    actions: normalizeActionItems(summary, overview),
    openQuestions: normalizeTextList(summary?.open_questions),
  };
}

function getSpeakerLabels(reportDetail) {
  return Array.from(
    new Set(
      (reportDetail?.speaker_transcript ?? [])
        .map((item) => item.speaker_label)
        .filter(Boolean),
    ),
  );
}

function getTranscriptMeta(reportDetail) {
  const segments = reportDetail?.speaker_transcript ?? [];
  const durationMs = Math.max(...segments.map((item) => Number(item.end_ms ?? 0)), 0);
  const speakers = getSpeakerLabels(reportDetail);

  return {
    duration: formatDuration(durationMs),
    participants: speakers.length > 0 ? speakers.join(", ") : "-",
    participantsCount: speakers.length || "-",
  };
}

function buildAgenda(recap, session) {
  const firstTopic = recap.topics.find((topic) => topic.title)?.title;
  const headline = session?.title || "";
  return firstTopic || headline || "회의 안건";
}

function getSessionSourceLabel(session) {
  return formatSourceLabel(
    session?.primary_input_source ||
      session?.input_source ||
      session?.source ||
      session?.recording_source,
  );
}

export {
  buildAgenda,
  buildRecapModel,
  formatTimestamp,
  getSessionSourceLabel,
  getTranscriptMeta,
};
