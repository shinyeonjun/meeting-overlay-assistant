import test from "node:test";
import assert from "node:assert/strict";

import {
    buildHitRects,
    createHitRectSync,
    hitRectsChanged,
    toHitRect,
} from "../src/controllers/ui/hit-rect-model.js";

function fakeTimers() {
    const pending = new Map();
    let nextId = 1;
    return {
        setTimer(callback) {
            const id = nextId++;
            pending.set(id, callback);
            return id;
        },
        clearTimer(id) {
            pending.delete(id);
        },
        pendingCount() {
            return pending.size;
        },
        runAll() {
            const callbacks = [...pending.values()];
            pending.clear();
            callbacks.forEach((callback) => callback());
        },
    };
}

test("DOMRect 값은 논리 좌표 그대로 hit rect가 된다 (DPR과 무관)", () => {
    const rect = { x: 10.5, y: 20, width: 300, height: 44, left: 10.5, top: 20 };
    assert.deepEqual(toHitRect(rect), { x: 10.5, y: 20, width: 300, height: 44 });
});

test("크기가 0이거나 숨겨진 요소의 rect는 제외한다", () => {
    const rects = buildHitRects([
        { x: 0, y: 0, width: 0, height: 0 },
        { x: 5, y: 5, width: 100, height: 0 },
        { x: 5, y: 5, width: 100, height: 50 },
    ]);
    assert.deepEqual(rects, [{ x: 5, y: 5, width: 100, height: 50 }]);
});

test("NaN이나 Infinity가 섞인 rect는 제외한다", () => {
    const rects = buildHitRects([
        { x: Number.NaN, y: 0, width: 10, height: 10 },
        { x: 0, y: 0, width: Number.POSITIVE_INFINITY, height: 10 },
        { x: 1, y: 2, width: 3, height: 4 },
    ]);
    assert.deepEqual(rects, [{ x: 1, y: 2, width: 3, height: 4 }]);
});

test("같은 선택자로 여러 요소가 잡혀도 모두 포함한다", () => {
    const rects = buildHitRects([
        { x: 0, y: 0, width: 10, height: 10 },
        { x: 20, y: 0, width: 10, height: 10 },
    ]);
    assert.equal(rects.length, 2);
});

test("hitRectsChanged는 길이나 좌표가 같을 때만 false를 돌려준다", () => {
    const a = [{ x: 0, y: 0, width: 10, height: 10 }];
    assert.equal(hitRectsChanged(null, a), true);
    assert.equal(hitRectsChanged(a, [{ x: 0, y: 0, width: 10, height: 10 }]), false);
    assert.equal(hitRectsChanged(a, [{ x: 1, y: 0, width: 10, height: 10 }]), true);
    assert.equal(hitRectsChanged(a, []), true);
});

test("flush는 첫 호출에 보내고, 같은 값이면 다시 보내지 않는다", () => {
    const sent = [];
    let domRects = [{ x: 0, y: 0, width: 10, height: 10 }];
    const timers = fakeTimers();
    const sync = createHitRectSync({
        collect: () => domRects,
        send: (rects) => sent.push(rects),
        delayMs: 32,
        setTimer: timers.setTimer,
        clearTimer: timers.clearTimer,
    });

    sync.flush();
    sync.flush();
    assert.equal(sent.length, 1);

    domRects = [{ x: 0, y: 0, width: 20, height: 10 }];
    sync.flush();
    assert.equal(sent.length, 2);
    assert.deepEqual(sent[1], [{ x: 0, y: 0, width: 20, height: 10 }]);
});

test("request는 delay 안의 여러 트리거를 한 번의 전송으로 합친다", () => {
    const sent = [];
    const timers = fakeTimers();
    const sync = createHitRectSync({
        collect: () => [{ x: 1, y: 1, width: 5, height: 5 }],
        send: (rects) => sent.push(rects),
        delayMs: 32,
        setTimer: timers.setTimer,
        clearTimer: timers.clearTimer,
    });

    sync.request();
    sync.request();
    sync.request();
    assert.equal(timers.pendingCount(), 1);
    timers.runAll();
    assert.equal(sent.length, 1);
});

test("request 뒤 값이 그대로면 타이머가 돌아도 전송하지 않는다", () => {
    const sent = [];
    const timers = fakeTimers();
    const sync = createHitRectSync({
        collect: () => [{ x: 1, y: 1, width: 5, height: 5 }],
        send: (rects) => sent.push(rects),
        delayMs: 32,
        setTimer: timers.setTimer,
        clearTimer: timers.clearTimer,
    });

    sync.flush();
    sync.request();
    timers.runAll();
    assert.equal(sent.length, 1);
});

test("flush는 대기 중인 request 타이머를 취소하고 즉시 계산한다", () => {
    const sent = [];
    const timers = fakeTimers();
    const sync = createHitRectSync({
        collect: () => [{ x: 2, y: 2, width: 5, height: 5 }],
        send: (rects) => sent.push(rects),
        delayMs: 32,
        setTimer: timers.setTimer,
        clearTimer: timers.clearTimer,
    });

    sync.request();
    sync.flush();
    assert.equal(timers.pendingCount(), 0);
    assert.equal(sent.length, 1);
});
