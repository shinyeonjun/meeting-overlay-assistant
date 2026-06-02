import test from "node:test";
import assert from "node:assert/strict";

import {
  AUDIO_SOURCE,
  LIVE_CONNECTION_MODE,
  resolveLiveConnectionMode,
  resolveTauriPrewarmSource,
} from "../src/audio/source-policy.js";

test("system audio uses Tauri only when runtime is available", () => {
  assert.equal(
    resolveLiveConnectionMode(AUDIO_SOURCE.SYSTEM_AUDIO, true),
    LIVE_CONNECTION_MODE.SYSTEM_AUDIO_TAURI,
  );
  assert.equal(
    resolveLiveConnectionMode(AUDIO_SOURCE.SYSTEM_AUDIO, false),
    LIVE_CONNECTION_MODE.SYSTEM_AUDIO_UNSUPPORTED,
  );
});

test("only Tauri audio modes request system audio prewarm", () => {
  assert.equal(
    resolveTauriPrewarmSource(AUDIO_SOURCE.SYSTEM_AUDIO, true),
    AUDIO_SOURCE.SYSTEM_AUDIO,
  );
  assert.equal(resolveTauriPrewarmSource(AUDIO_SOURCE.MIXED, true), AUDIO_SOURCE.SYSTEM_AUDIO);
  assert.equal(resolveTauriPrewarmSource(AUDIO_SOURCE.MIC, true), null);
  assert.equal(resolveTauriPrewarmSource(AUDIO_SOURCE.SYSTEM_AUDIO, false), null);
});
