import test from "node:test";
import assert from "node:assert/strict";

import { applyLiveEvents } from "../src/state/live-store.js";
import { applyOverview, setSession } from "../src/state/session/meeting-session-store.js";
import {
  createEmptyOverviewBuckets,
  mergeOverviewBuckets,
} from "../src/state/session/overview-state.js";

function createMockState() {
  return {
    session: {
      id: null,
      status: "idle",
      overview: createEmptyOverviewBuckets(),
      liveOverview: createEmptyOverviewBuckets(),
    },
  };
}

test("live question은 overview polling 이후에도 merged view에 남는다", () => {
  const state = createMockState();

  setSession(state, {
    id: "session-1",
    status: "running",
  });

  applyLiveEvents(state, [
    {
      id: "live-question-1",
      type: "question",
      title: "배포 일정은 언제 확정되나요?",
      state: "open",
      speaker_label: null,
    },
  ]);

  applyOverview(state, {
    currentTopic: "배포 일정 논의",
    questions: [],
    decisions: [],
    actionItems: [],
    risks: [],
  });

  const mergedOverview = mergeOverviewBuckets(
    state.session.overview,
    state.session.liveOverview,
  );

  assert.equal(mergedOverview.questions.length, 1);
  assert.equal(mergedOverview.questions[0].id, "live-question-1");
  assert.equal(state.session.overview.questions.length, 0);
  assert.equal(state.session.liveOverview.questions.length, 1);
});

test("세션이 종료되면 live overview 질문은 초기화된다", () => {
  const state = createMockState();

  setSession(state, {
    id: "session-1",
    status: "running",
  });

  applyLiveEvents(state, [
    {
      id: "live-question-1",
      type: "question",
      title: "배포 일정은 언제 확정되나요?",
      state: "open",
      speaker_label: null,
    },
  ]);

  setSession(state, {
    id: "session-1",
    status: "ended",
  });

  assert.equal(state.session.liveOverview.questions.length, 0);
});
