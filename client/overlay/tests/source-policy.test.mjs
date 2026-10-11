import test from "node:test";
import assert from "node:assert/strict";

import {
    AUDIO_SOURCE,
    LIVE_CONNECTION_MODE,
    isClientSourceReady,
    resolveLiveConnectionMode,
} from "../src/audio/source-policy.js";

test("Tauri에서 마이크는 로컬 STT 백엔드 경로다", () => {
    assert.equal(
        resolveLiveConnectionMode(AUDIO_SOURCE.MIC, true),
        LIVE_CONNECTION_MODE.MIC_LOCAL_TAURI,
    );
});

test("브라우저에서 로컬 STT 마이크는 지원되지 않는다", () => {
    assert.equal(
        resolveLiveConnectionMode(AUDIO_SOURCE.MIC, false),
        LIVE_CONNECTION_MODE.MIC_LOCAL_UNSUPPORTED,
    );
});

test("혼합 입력은 Tauri에서만 로컬 STT 백엔드 경로를 쓴다", () => {
    assert.equal(
        resolveLiveConnectionMode(AUDIO_SOURCE.MIXED, true),
        LIVE_CONNECTION_MODE.MIXED_LOCAL_TAURI,
    );
    assert.equal(
        resolveLiveConnectionMode(AUDIO_SOURCE.MIXED, false),
        LIVE_CONNECTION_MODE.MIXED_LOCAL_UNSUPPORTED,
    );
});

test("로컬 STT 마이크는 백엔드 준비 상태가 있어야 준비됨이다", () => {
    assert.equal(isClientSourceReady(AUDIO_SOURCE.MIC, {}, false), false);
    assert.equal(
        isClientSourceReady(AUDIO_SOURCE.MIC, { mic: { ready: true } }, false),
        true,
    );
});
