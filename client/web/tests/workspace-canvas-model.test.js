import test from "node:test";
import assert from "node:assert/strict";

import {
  buildPollingPlan,
  canPlayTranscriptRow,
  formatAudioClock,
  formatTranscriptTime,
  POST_PROCESSING_POLL_INTERVAL_MS,
  REPORT_GENERATION_POLL_INTERVAL_MS,
} from "../src/features/workspace/workspace-canvas-model.js";

test("발화 시각은 1시간 전에는 mm:ss, 그 뒤에는 hh:mm:ss로 보인다", () => {
  assert.equal(formatTranscriptTime(0), "00:00");
  assert.equal(formatTranscriptTime(65_000), "01:05");
  assert.equal(formatTranscriptTime(3_725_000), "01:02:05");
  assert.equal(formatTranscriptTime(-5_000), "00:00");
});

test("오디오 재생 시계는 음수와 NaN을 0으로 본다", () => {
  assert.equal(formatAudioClock(59.9), "00:59");
  assert.equal(formatAudioClock(3661), "01:01:01");
  assert.equal(formatAudioClock(Number.NaN), "00:00");
  assert.equal(formatAudioClock(-3), "00:00");
});

test("끝 시각이 시작보다 커야 재생할 수 있다", () => {
  assert.equal(canPlayTranscriptRow({ startMs: 0, endMs: 1000 }), true);
  assert.equal(canPlayTranscriptRow({ startMs: 1000, endMs: 1000 }), false);
  assert.equal(canPlayTranscriptRow({ startMs: Number.NaN, endMs: 5 }), false);
  assert.equal(canPlayTranscriptRow(undefined), false);
});

test("실시간 세션은 폴링 계획이 없다", () => {
  assert.equal(
    buildPollingPlan({ isLive: true, reportStatus: null, workflow: { pipelineStage: "post_processing", status: "processing" } }),
    null,
  );
});

test("후처리가 진행 중이면 후처리 폴링을 돌린다", () => {
  const plan = buildPollingPlan({
    isLive: false,
    reportStatus: null,
    workflow: { pipelineStage: "post_processing", status: "pending" },
  });
  assert.equal(plan.phase, "post_processing");
  assert.equal(plan.intervalMs, POST_PROCESSING_POLL_INTERVAL_MS);
  assert.equal(plan.loadOptions.includeTranscript, true);
});

test("리포트 생성 작업이 진행 중이면 리포트 상세를 폴링한다", () => {
  const plan = buildPollingPlan({
    isLive: false,
    reportStatus: { latest_job_status: "PROCESSING" },
    workflow: { pipelineStage: "report_generation", status: "ready" },
  });
  assert.equal(plan.phase, "report_generation");
  assert.equal(plan.intervalMs, REPORT_GENERATION_POLL_INTERVAL_MS);
  assert.equal(plan.loadOptions.includeReportDetail, true);
});

test("진행 중인 작업이 없으면 폴링하지 않는다", () => {
  assert.equal(
    buildPollingPlan({ isLive: false, reportStatus: null, workflow: { pipelineStage: "done", status: "ready" } }),
    null,
  );
});
