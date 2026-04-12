/** 오버레이에서 공통 흐름의 ui bridge controller 제어를 담당한다. */
import { invokeTauri } from "../../services/tauri-live-audio.js";
import { clampFloatingLayout } from "./ui-layout-controller.js";

const UI_HIT_SELECTORS = [
    ".caption-box",
    ".fab-button",
    ".workspace:not(.collapsed)",
    ".auth-panel",
];

export function setupTauriUiBridge() {
    sendUIRects();
    window.setInterval(sendUIRects, 500);
    window.addEventListener("resize", () => {
        clampFloatingLayout();
        sendUIRects();
    });
}

export function sendUIRects() {
    const rects = UI_HIT_SELECTORS.flatMap((selector) => {
        const element = document.querySelector(selector);
        if (!element) {
            return [];
        }

        const rect = element.getBoundingClientRect();
        return [{
            x: rect.x,
            y: rect.y,
            width: rect.width,
            height: rect.height,
        }];
    });

    invokeTauri("register_ui_rects", { rects }).catch(() => {});
}
