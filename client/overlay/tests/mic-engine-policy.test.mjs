import test from "node:test";
import assert from "node:assert/strict";

import { DEFAULT_MIC_ENGINE, MIC_ENGINE, normalizeMicEngine } from "../src/audio/mic-engine.js";
import {
    AUDIO_SOURCE,
    LIVE_CONNECTION_MODE,
    isClientSourceReady,
    resolveLiveConnectionMode,
} from "../src/audio/source-policy.js";

test("마이크 엔진 기본값은 로컬 STT다", () => {
    assert.equal(DEFAULT_MIC_ENGINE, MIC_ENGINE.LOCAL);
    assert.equal(normalizeMicEngine(undefined), MIC_ENGINE.LOCAL);
    assert.equal(normalizeMicEngine("unknown"), MIC_ENGINE.LOCAL);
    assert.equal(normalizeMicEngine("web_speech"), MIC_ENGINE.WEB_SPEECH);
});

test("Tauri에서 마이크 기본 모드는 로컬 STT 백엔드 경로다", () => {
    assert.equal(
        resolveLiveConnectionMode(AUDIO_SOURCE.MIC, true, MIC_ENGINE.LOCAL),
        LIVE_CONNECTION_MODE.MIC_LOCAL_TAURI,
    );
});

test("브라우저에서 로컬 STT 마이크는 지원되지 않는다", () => {
    assert.equal(
        resolveLiveConnectionMode(AUDIO_SOURCE.MIC, false, MIC_ENGINE.LOCAL),
        LIVE_CONNECTION_MODE.MIC_LOCAL_UNSUPPORTED,
    );
});

test("Web Speech는 사용자가 켠 경우에만 쓴다", () => {
    assert.equal(
        resolveLiveConnectionMode(AUDIO_SOURCE.MIC, false, MIC_ENGINE.WEB_SPEECH),
        LIVE_CONNECTION_MODE.MIC_WEB_SPEECH,
    );
    assert.equal(
        resolveLiveConnectionMode(AUDIO_SOURCE.MIC, true, MIC_ENGINE.WEB_SPEECH),
        LIVE_CONNECTION_MODE.MIC_WEB_SPEECH,
    );
});

test("혼합 입력은 엔진과 런타임에 따라 모드가 갈린다", () => {
    assert.equal(
        resolveLiveConnectionMode(AUDIO_SOURCE.MIXED, true, MIC_ENGINE.LOCAL),
        LIVE_CONNECTION_MODE.MIXED_LOCAL_TAURI,
    );
    assert.equal(
        resolveLiveConnectionMode(AUDIO_SOURCE.MIXED, false, MIC_ENGINE.LOCAL),
        LIVE_CONNECTION_MODE.MIXED_LOCAL_UNSUPPORTED,
    );
    assert.equal(
        resolveLiveConnectionMode(AUDIO_SOURCE.MIXED, true, MIC_ENGINE.WEB_SPEECH),
        LIVE_CONNECTION_MODE.MIXED_TAURI,
    );
});

test("로컬 STT 마이크는 백엔드 준비 상태가 있어야 준비됨이다", () => {
    assert.equal(isClientSourceReady(AUDIO_SOURCE.MIC, {}, false, MIC_ENGINE.LOCAL), false);
    assert.equal(
        isClientSourceReady(AUDIO_SOURCE.MIC, { mic: { ready: true } }, false, MIC_ENGINE.LOCAL),
        true,
    );
});

test("Node 환경(브라우저 API 없음)에서는 Web Speech가 준비되지 않는다", () => {
    assert.equal(isClientSourceReady(AUDIO_SOURCE.MIC, {}, false, MIC_ENGINE.WEB_SPEECH), false);
});
