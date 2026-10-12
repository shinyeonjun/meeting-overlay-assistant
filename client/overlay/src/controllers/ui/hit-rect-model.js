// 클릭 통과 hit rect 계산의 순수 로직. DOM과 Tauri에 접근하지 않는다.
//
// 좌표계: 입력은 getBoundingClientRect() 결과(뷰포트 기준 CSS px = 논리 px)다.
// Rust 쪽 hit test는 커서의 물리 좌표를 window scale factor로 나눠 논리 좌표로
// 바꾼 뒤 이 rect와 비교한다(main.rs의 `rx = (cx - win_pos.x) / scale`).
// 따라서 rect를 물리 px로 바꾸면 Rust 비교가 깨진다. 여기서는 변환하지 않고
// 논리 좌표 그대로 보낸다. 물리 변환이 필요해지면 Rust 비교 로직과 함께 바꿔야 한다.

export function toHitRect(rect) {
    const x = Number(rect?.x ?? rect?.left);
    const y = Number(rect?.y ?? rect?.top);
    const width = Number(rect?.width);
    const height = Number(rect?.height);
    if (![x, y, width, height].every(Number.isFinite)) {
        return null;
    }
    // 숨겨진(display:none 등) 요소는 0 크기 rect가 나오므로 제외한다.
    if (width <= 0 || height <= 0) {
        return null;
    }
    return { x, y, width, height };
}

export function buildHitRects(domRects) {
    const rects = [];
    for (const rect of domRects) {
        const hit = toHitRect(rect);
        if (hit) {
            rects.push(hit);
        }
    }
    return rects;
}

export function hitRectsChanged(previous, next) {
    if (!previous || previous.length !== next.length) {
        return true;
    }
    return next.some((rect, index) => {
        const prev = previous[index];
        return rect.x !== prev.x
            || rect.y !== prev.y
            || rect.width !== prev.width
            || rect.height !== prev.height;
    });
}

// 여러 트리거(resize, scroll, DOM 변경, 주기 백업)를 delayMs 안에서 한 번으로 합치고,
// 이전에 보낸 값과 같으면 전송하지 않는다. 타이머는 주입받아 테스트 가능하게 한다.
export function createHitRectSync({ collect, send, delayMs, setTimer, clearTimer }) {
    let last = null;
    let timer = null;

    function run() {
        timer = null;
        const rects = buildHitRects(collect());
        if (last !== null && !hitRectsChanged(last, rects)) {
            return;
        }
        last = rects;
        send(rects);
    }

    // trailing throttle: 대기 중인 실행이 없으면 delayMs 뒤 한 번 실행한다.
    function request() {
        if (timer === null) {
            timer = setTimer(run, delayMs);
        }
    }

    // 즉시 계산하고 바뀌었을 때만 보낸다.
    function flush() {
        if (timer !== null) {
            clearTimer(timer);
        }
        run();
    }

    return { request, flush };
}
