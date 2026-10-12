import { invokeTauri } from "../../services/tauri-live-audio.js";
import { clampFloatingLayout } from "./ui-layout-controller.js";
import { createHitRectSync } from "./hit-rect-model.js";

const UI_HIT_SELECTORS = [
    ".caption-box",
    ".fab-button",
    ".workspace:not(.collapsed)",
    ".auth-panel",
];

// transition 중에는 DOM 이벤트가 없으므로 주기 백업으로 한 번 더 맞춘다.
const BACKSTOP_INTERVAL_MS = 500;
const COALESCE_DELAY_MS = 32;

const hitSync = createHitRectSync({
    collect: collectUiElementRects,
    send: (rects) => {
        invokeTauri("register_ui_rects", { rects }).catch(() => {});
    },
    delayMs: COALESCE_DELAY_MS,
    setTimer: (callback, delay) => window.setTimeout(callback, delay),
    clearTimer: (id) => window.clearTimeout(id),
});

export function setupTauriUiBridge() {
    sendUIRects();
    window.setInterval(() => hitSync.request(), BACKSTOP_INTERVAL_MS);
    window.addEventListener("resize", () => {
        clampFloatingLayout();
        hitSync.request();
    });
    window.addEventListener("scroll", () => hitSync.request(), { capture: true, passive: true });
    if (typeof MutationObserver === "function") {
        const observer = new MutationObserver(() => hitSync.request());
        observer.observe(document.body, {
            subtree: true,
            childList: true,
            characterData: true,
            attributes: true,
            attributeFilter: ["class", "style"],
        });
    }
}

// 같은 선택자에 맞는 모든 요소를 실제 DOM 좌표로 수집한다.
function collectUiElementRects() {
    return UI_HIT_SELECTORS.flatMap((selector) =>
        Array.from(document.querySelectorAll(selector), (element) => element.getBoundingClientRect()),
    );
}

export function sendUIRects() {
    hitSync.flush();
}
