/** 오버레이 런타임의 wait 모듈이다. */
export function wait(milliseconds) {
    return new Promise((resolve) => window.setTimeout(resolve, milliseconds));
}
