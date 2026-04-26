import test from "node:test";
import assert from "node:assert/strict";

import { shouldTreatAsUnexpectedSessionDisconnect } from "../src/controllers/session/session-disconnect-policy.js";

test("네트워크 fetch 실패는 세션 연결 끊김으로 본다", () => {
  const error = new TypeError("Failed to fetch");

  assert.equal(shouldTreatAsUnexpectedSessionDisconnect(error), true);
});

test("session overview 404는 세션 연결 끊김으로 본다", () => {
  const error = new Error("HTTP 404: /api/v1/sessions/session-1/overview");

  assert.equal(shouldTreatAsUnexpectedSessionDisconnect(error), true);
});

test("일반적인 500 응답은 즉시 세션 종료로 보지 않는다", () => {
  const error = new Error("HTTP 500: /api/v1/sessions/session-1/overview");

  assert.equal(shouldTreatAsUnexpectedSessionDisconnect(error), false);
});
