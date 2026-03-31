import test from "node:test";
import assert from "node:assert/strict";

import { executeSessionEndingFlow } from "../src/controllers/session/session-ending-flow.js";

test("endSession이 실패하면 live stop은 호출되지 않는다", async () => {
  let stopCalled = false;

  await assert.rejects(
    () =>
      executeSessionEndingFlow({
        sessionId: "session-1",
        requestSessionEnd: async () => {
          throw new Error("end failed");
        },
        stopLiveConnection: async () => {
          stopCalled = true;
        },
      }),
    /end failed/,
  );

  assert.equal(stopCalled, false);
});

test("endSession 성공 후 live stop 실패는 cleanupError로 분리된다", async () => {
  const result = await executeSessionEndingFlow({
    sessionId: "session-2",
    requestSessionEnd: async () => ({
      id: "session-2",
      status: "ended",
    }),
    stopLiveConnection: async () => {
      throw new Error("cleanup failed");
    },
  });

  assert.deepEqual(result.endedSessionPayload, {
    id: "session-2",
    status: "ended",
  });
  assert.match(result.cleanupError?.message ?? "", /cleanup failed/);
});
