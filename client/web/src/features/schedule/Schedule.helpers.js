export const WEEKDAY_LABELS = ["일", "월", "화", "수", "목", "금", "토"];
export const EVENT_TONES = ["primary", "indigo", "emerald", "amber", "slate"];

function normalizeSearch(value) {
  return String(value ?? "").trim().toLowerCase();
}

export function matchesSearch(session, query) {
  const normalized = normalizeSearch(query);
  if (!normalized) {
    return true;
  }
  return [session.title, session.status, session.primary_input_source]
    .filter(Boolean)
    .join(" ")
    .toLowerCase()
    .includes(normalized);
}

export function dedupeSessions(...groups) {
  const seen = new Set();
  return groups
    .flat()
    .filter(Boolean)
    .filter((session) => {
      if (seen.has(session.id)) {
        return false;
      }
      seen.add(session.id);
      return true;
    });
}

export function getSessionDate(session) {
  const value = session?.started_at || session?.created_at;
  const date = value ? new Date(value) : null;
  return date && !Number.isNaN(date.getTime()) ? date : null;
}

export function startOfWeek(date) {
  const next = new Date(date);
  next.setHours(0, 0, 0, 0);
  next.setDate(next.getDate() - next.getDay());
  return next;
}

export function addDays(date, days) {
  const next = new Date(date);
  next.setDate(next.getDate() + days);
  return next;
}

export function isSameDay(left, right) {
  return (
    left.getFullYear() === right.getFullYear() &&
    left.getMonth() === right.getMonth() &&
    left.getDate() === right.getDate()
  );
}

export function formatMonthLabel(date) {
  return new Intl.DateTimeFormat("ko-KR", {
    month: "long",
    year: "numeric",
  }).format(date);
}

export function formatCardDate(date) {
  return new Intl.DateTimeFormat("ko-KR", {
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
    month: "short",
  }).format(date);
}
