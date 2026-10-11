import test from "node:test";
import assert from "node:assert/strict";

import { resolveStartBlockReason } from "../src/controllers/runtime/start-readiness.js";

const READY = {
    sessionId: "session-1",
    sessionStatus: "draft",
    serverReady: true,
    clientReady: true,
    warming: false,
    source: "mic",
};

test("모든 조건이 맞으면 막힌 이유가 없다", () => {
    assert.equal(resolveStartBlockReason(READY), null);
});

test("세션이 없으면 세션을 먼저 만들라고 안내한다", () => {
    assert.match(resolveStartBlockReason({ ...READY, sessionId: null }), /세션/);
});

test("서버가 준비 중이면 기다리라고, 연결이 안 되면 서버를 확인하라고 나눠 안내한다", () => {
    assert.match(resolveStartBlockReason({ ...READY, serverReady: false, warming: true }), /준비하는 중/);
    assert.match(resolveStartBlockReason({ ...READY, serverReady: false, warming: false }), /서버에 연결/);
});

test("입력 장치가 준비되지 않으면 어떤 입력인지 한국어로 알려준다", () => {
    assert.match(
        resolveStartBlockReason({ ...READY, clientReady: false, source: "system_audio" }),
        /시스템 오디오 입력/,
    );
});

test("이미 시작된 세션은 시작할 수 없다고 안내한다", () => {
    assert.match(resolveStartBlockReason({ ...READY, sessionStatus: "running" }), /이미 시작/);
});
