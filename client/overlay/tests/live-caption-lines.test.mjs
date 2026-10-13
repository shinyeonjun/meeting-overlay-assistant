import test from "node:test";
import assert from "node:assert/strict";

import { applyLiveUtterance, finalizeCurrentUtterance } from "../src/state/live-store.js";

const LIMIT = 8;

function createMockState() {
  return {
    live: {
      currentUtterance: null,
      transcriptHistory: [],
      activeLineFinalizeTimerId: null,
      seenFeedEventIds: new Set(),
      metrics: { recentFinalizeEvents: [] },
    },
    session: {},
  };
}

function preview(segmentId, text) {
  return { id: `p-${text}`, segment_id: segmentId, text, kind: "preview", stability: "low", is_partial: true };
}

function liveFinal(segmentId, text) {
  return { id: `l-${text}`, segment_id: segmentId, text, kind: "live_final", stability: "medium", is_partial: true };
}

function archiveFinal(segmentId, text) {
  return { id: `a-${text}`, segment_id: segmentId, text, kind: "archive_final", is_partial: false };
}

test("쉼 없이 회색 자막에서 확정 자막으로 가면 그 구간 줄은 한 번만 나온다", () => {
  const state = createMockState();

  assert.deepEqual(applyLiveUtterance(state, preview("seg-1", "오늘날"), LIMIT).completedLines, []);
  assert.deepEqual(applyLiveUtterance(state, liveFinal("seg-1", "오늘날 날개를"), LIMIT).completedLines, []);
  const done = applyLiveUtterance(state, archiveFinal("seg-1", "오늘날 날개를 접을 수 없는 곤충은"), LIMIT);

  assert.deepEqual(done.completedLines, [{ text: "오늘날 날개를 접을 수 없는 곤충은", segmentId: "seg-1" }]);
});

test("쉼으로 먼저 닫힌 줄에 같은 구간 회색 자막이 다시 오면 줄을 다시 열고 새 줄을 쌓지 않는다", () => {
  const state = createMockState();

  applyLiveUtterance(state, preview("seg-1", "저울의 북발트"), LIMIT);
  const closedBySilence = finalizeCurrentUtterance(state, LIMIT, "silence");
  assert.deepEqual(closedBySilence, { text: "저울의 북발트", segmentId: "seg-1" });

  const reopened = applyLiveUtterance(state, preview("seg-1", "저울의 북발트회를 건낼 경우"), LIMIT);

  // 예전에는 단계가 final에 묶여 여기서 바로 다시 확정 처리되며 목록에 새 줄이 쌓였다.
  assert.deepEqual(reopened.completedLines, []);
  assert.equal(state.live.currentUtterance.phase, "draft");
  assert.equal(state.live.currentUtterance.isCommitted, false);
  assert.equal(reopened.shouldScheduleFinalize, true);
});

test("쉼으로 닫힌 줄에 확정 자막이 오면 같은 구간 줄을 확정 글자로 고친다", () => {
  const state = createMockState();

  applyLiveUtterance(state, preview("seg-1", "저울의 북발트회를"), LIMIT);
  finalizeCurrentUtterance(state, LIMIT, "silence");
  applyLiveUtterance(state, preview("seg-1", "저울의 북발트회를 건낼 경우에는"), LIMIT);
  const secondSilence = finalizeCurrentUtterance(state, LIMIT, "silence");
  assert.deepEqual(secondSilence, { text: "저울의 북발트회를 건낼 경우에는", segmentId: "seg-1" });

  const final = applyLiveUtterance(state, archiveFinal("seg-1", "겨울에 북발트해를 건널 경우에는"), LIMIT);

  // 예전에는 이미 닫힌 줄이라 null을 돌려 확정 자막이 목록에 들어가지 않았다.
  assert.deepEqual(final.completedLines, [{ text: "겨울에 북발트해를 건널 경우에는", segmentId: "seg-1" }]);
  assert.equal(state.live.transcriptHistory.length, 1);
  assert.equal(state.live.transcriptHistory[0].text, "겨울에 북발트해를 건널 경우에는");
});

test("쉼으로 닫힌 뒤 글자가 그대로인 확정이 오면 다시 내보내지 않는다", () => {
  const state = createMockState();

  applyLiveUtterance(state, preview("seg-1", "마찬가지로"), LIMIT);
  finalizeCurrentUtterance(state, LIMIT, "silence");
  const final = applyLiveUtterance(state, archiveFinal("seg-1", "마찬가지로"), LIMIT);

  assert.deepEqual(final.completedLines, []);
});

test("다음 구간이 시작되면 이전 구간 줄은 한 번만 닫힌다", () => {
  const state = createMockState();

  applyLiveUtterance(state, preview("seg-1", "포클랜드의 공식"), LIMIT);
  const next = applyLiveUtterance(state, preview("seg-2", "일영국"), LIMIT);

  assert.deepEqual(next.completedLines, [{ text: "포클랜드의 공식", segmentId: "seg-1" }]);
  assert.equal(state.live.currentUtterance.segmentId, "seg-2");
});

test("늦은 확정은 해당 구간 줄로 나온다", () => {
  const state = createMockState();

  const late = applyLiveUtterance(
    state,
    { id: "late-1", segment_id: "seg-9", text: "늦게 온 확정", kind: "late_archive_final" },
    LIMIT,
  );

  assert.deepEqual(late.completedLines, [{ text: "늦게 온 확정", segmentId: "seg-9" }]);
});
