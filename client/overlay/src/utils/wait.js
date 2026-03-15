export function wait(milliseconds) {
    return new Promise((resolve) => window.setTimeout(resolve, milliseconds));
}
