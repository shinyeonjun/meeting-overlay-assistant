import test from "node:test";
import assert from "node:assert/strict";

import {
  hasRecordingAvailable,
  isStaleWorkspaceResponse,
  shouldClearActionNoticeAfterLoad,
  shouldFetchLatestReport,
} from "../src/features/workspace/workspace-canvas-model.js";

test("녹음 파일이 연결된 세션만 원본 재생과 다운로드를 노출한다", () => {
  assert.equal(hasRecordingAvailable({ recording_available: true }), true);
  assert.equal(hasRecordingAvailable({ recording_artifact_id: "artifact-1" }), true);
  assert.equal(hasRecordingAvailable({}), false);
  assert.equal(hasRecordingAvailable(null), false);
});

test("리포트 상세는 완료 상태이고 리포트 id가 있을 때만 다시 가져온다", () => {
  const completed = { status: "completed", latest_report_id: "report-1" };
  assert.equal(shouldFetchLatestReport(completed, true), true);
  assert.equal(shouldFetchLatestReport(completed, false), false);
  assert.equal(shouldFetchLatestReport({ status: "processing", latest_report_id: "report-1" }, true), false);
  assert.equal(shouldFetchLatestReport({ status: "completed", latest_report_id: null }, true), false);
});

test("요청 번호나 세션이 현재와 다른 응답은 오래된 응답으로 본다", () => {
  const current = { latestRequestId: 2, latestSessionId: "s1", requestId: 2, requestedSessionId: "s1" };
  assert.equal(isStaleWorkspaceResponse(current), false);
  assert.equal(isStaleWorkspaceResponse({ ...current, requestId: 1 }), true);
  assert.equal(isStaleWorkspaceResponse({ ...current, latestSessionId: "s2" }), true);
});

test("완료 또는 후처리 종료 상태를 적재하면 액션 안내를 지운다", () => {
  assert.equal(shouldClearActionNoticeAfterLoad({ status: "completed" }, null), true);
  assert.equal(
    shouldClearActionNoticeAfterLoad({ status: "pending" }, { session: { post_processing_status: "failed" } }),
    true,
  );
  assert.equal(
    shouldClearActionNoticeAfterLoad({ status: "pending" }, { session: { post_processing_status: "queued" } }),
    false,
  );
  assert.equal(shouldClearActionNoticeAfterLoad({ status: "pending" }, null), false);
});
