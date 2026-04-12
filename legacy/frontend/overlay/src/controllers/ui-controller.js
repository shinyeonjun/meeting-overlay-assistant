/**
 * UI 컨트롤러 — 드래그, 탭 전환, 워크스페이스, 캡션 접기, Tauri 브리지
 */

import { elements } from "../dom/elements.js";
import { invokeTauri } from "../services/tauri-live-audio.js";

// 클릭 투과 판정에 쓰이는 CSS 셀렉터
const UI_HIT_SELECTORS = [".caption-box", ".fab-button", ".workspace:not(.collapsed)"];

// localStorage 위치 저장 키
const POSITION_KEY = "caps-overlay-positions";

/* ───────────────────────────────── Tauri UI 브리지 ─── */

/** Tauri 쪽에 UI 요소 좌표를 주기적으로 전달한다. */
export function setupTauriUiBridge() {
    sendUIRects();
    window.setInterval(sendUIRects, 500);
    window.addEventListener("resize", () => {
        clampFloatingLayout();
        sendUIRects();
    });
}

/** 현재 보이는 UI 히트 영역 좌표를 Rust에 전송한다. */
export function sendUIRects() {
    const rects = UI_HIT_SELECTORS.flatMap((selector) => {
        const element = document.querySelector(selector);
        if (!element) {
            return [];
        }

        const rect = element.getBoundingClientRect();
        return [{ x: rect.x, y: rect.y, width: rect.width, height: rect.height }];
    });

    invokeTauri("register_ui_rects", { rects }).catch(() => { });
}

/* ───────────────────────────────── 드래그 ─── */

/** 캡션 박스와 워크스페이스를 드래그 가능하게 만든다. */
export function setupDraggableLayout() {
    restorePositions();

    const captionHeader = document.querySelector(".caption-header");
    if (captionHeader) {
        makeDraggable(captionHeader, elements.captionBox, "captionBox");
    }

    const workspaceHeader = document.querySelector(".workspace-header");
    if (workspaceHeader) {
        makeDraggable(workspaceHeader, elements.workspace, "workspace");
    }

    setupFabDrag();
}

/** handle을 잡아 target을 드래그하는 동작을 바인딩한다. */
function makeDraggable(handle, target, storageKey) {
    let startX = 0;
    let startY = 0;
    let originX = 0;
    let originY = 0;

    handle.addEventListener("mousedown", (event) => {
        if (event.target.closest("button")) {
            return;
        }

        event.preventDefault();

        const rect = target.getBoundingClientRect();
        target.style.left = `${rect.left}px`;
        target.style.top = `${rect.top}px`;
        target.style.right = "auto";
        target.style.bottom = "auto";
        target.style.transform = "none";

        startX = event.clientX;
        startY = event.clientY;
        originX = rect.left;
        originY = rect.top;

        const onMove = (moveEvent) => {
            target.style.left = `${originX + moveEvent.clientX - startX}px`;
            target.style.top = `${originY + moveEvent.clientY - startY}px`;
        };

        const onUp = () => {
            document.removeEventListener("mousemove", onMove);
            document.removeEventListener("mouseup", onUp);
            sendUIRects();
            if (storageKey) {
                savePosition(storageKey, target);
            }
        };

        document.addEventListener("mousemove", onMove);
        document.addEventListener("mouseup", onUp);
    });

    handle.style.cursor = "grab";
    handle.addEventListener("mousedown", () => {
        handle.style.cursor = "grabbing";
    });
    document.addEventListener("mouseup", () => {
        handle.style.cursor = "grab";
    });
}

/** FAB 버튼을 드래그 가능하게 하되, 5px 미만이면 클릭(토글)으로 처리한다. */
function setupFabDrag() {
    const fab = elements.togglePanel;
    if (!fab) {
        return;
    }

    let startX = 0;
    let startY = 0;
    let originX = 0;
    let originY = 0;
    let dragged = false;

    fab.addEventListener("mousedown", (event) => {
        event.preventDefault();

        const rect = fab.getBoundingClientRect();
        fab.style.left = `${rect.left}px`;
        fab.style.top = `${rect.top}px`;
        fab.style.right = "auto";
        fab.style.bottom = "auto";

        startX = event.clientX;
        startY = event.clientY;
        originX = rect.left;
        originY = rect.top;
        dragged = false;

        const onMove = (moveEvent) => {
            const deltaX = moveEvent.clientX - startX;
            const deltaY = moveEvent.clientY - startY;

            if (Math.abs(deltaX) > 5 || Math.abs(deltaY) > 5) {
                dragged = true;
            }

            if (!dragged) {
                return;
            }

            fab.style.left = `${originX + deltaX}px`;
            fab.style.top = `${originY + deltaY}px`;
        };

        const onUp = () => {
            document.removeEventListener("mousemove", onMove);
            document.removeEventListener("mouseup", onUp);

            if (!dragged) {
                if (elements.workspace.classList.contains("collapsed")) {
                    openWorkspace();
                } else {
                    closeWorkspace();
                }
            }

            sendUIRects();
        };

        document.addEventListener("mousemove", onMove);
        document.addEventListener("mouseup", onUp);
    });
}

/* ───────────────────────────────── 워크스페이스 / 탭 ─── */

/** 워크스페이스 패널을 연다. */
export function openWorkspace() {
    elements.workspace.classList.remove("collapsed");
    elements.workspace.setAttribute("aria-hidden", "false");
    elements.togglePanel.classList.add("active");
    sendUIRects();
}

/** 워크스페이스 패널을 닫는다. */
export function closeWorkspace() {
    elements.workspace.classList.add("collapsed");
    elements.workspace.setAttribute("aria-hidden", "true");
    elements.togglePanel.classList.remove("active");
    sendUIRects();
}

/** 지정한 탭을 활성화한다. */
export function activateTab(tabName) {
    for (const tab of elements.tabs) {
        tab.classList.toggle("active", tab.dataset.tab === tabName);
    }

    for (const body of elements.tabBodies) {
        body.classList.toggle("active", body.id === `tab-${tabName}`);
    }
}

/** 캡션 박스 본문 접기/펼치기 토글. */
export function toggleCaptionBody() {
    const isCollapsed = elements.captionBox.classList.toggle("collapsed");
    elements.captionToggle.textContent = isCollapsed ? "+" : "−";
}

/* ───────────────────────────────── 유틸 ─── */

/** 상태 배지를 갱신한다. */
export function setStatus(element, text, tone) {
    element.textContent = text;
    element.className = `badge ${tone}`;
}

const FLASH_DURATION_MS = 3000;
const flashTimers = new WeakMap();

/** 배지를 일시적으로 변경한 뒤 원래 상태로 복원한다. alert() 대체용. */
export function flashStatus(element, text, tone = "error") {
    const prevText = element.textContent;
    const prevClass = element.className;

    setStatus(element, text, tone);

    const existingTimer = flashTimers.get(element);
    if (existingTimer) {
        clearTimeout(existingTimer);
    }

    flashTimers.set(
        element,
        setTimeout(() => {
            element.textContent = prevText;
            element.className = prevClass;
            flashTimers.delete(element);
        }, FLASH_DURATION_MS),
    );
}

/* ───────────────────────────────── 위치 기억 ─── */

/** 드래그된 요소의 위치를 localStorage에 저장한다. */
function savePosition(key, target) {
    try {
        const stored = JSON.parse(localStorage.getItem(POSITION_KEY) || "{}");
        stored[key] = {
            left: target.style.left,
            top: target.style.top,
        };
        localStorage.setItem(POSITION_KEY, JSON.stringify(stored));
    } catch { /* localStorage 불가 시 무시 */ }
}

/** 저장된 위치를 복원한다. */
function restorePositions() {
    try {
        const stored = JSON.parse(localStorage.getItem(POSITION_KEY) || "{}");
        const targets = {
            captionBox: elements.captionBox,
            workspace: elements.workspace,
        };

        for (const [key, target] of Object.entries(targets)) {
            if (stored[key] && target) {
                target.style.left = stored[key].left;
                target.style.top = stored[key].top;
                target.style.right = "auto";
                target.style.bottom = "auto";
                target.style.transform = "none";
            }
        }

        clampFloatingLayout();
    } catch { /* localStorage 불가 시 무시 */ }
}

function clampFloatingLayout() {
    clampElementToViewport(elements.captionBox, { margin: 12, fallbackBottom: 24, fallbackLeft: null });
    clampElementToViewport(elements.workspace, { margin: 12, fallbackTop: 24, fallbackRight: 24 });
    clampElementToViewport(elements.togglePanel, { margin: 12, fallbackBottom: 20, fallbackRight: 20 });
}

function clampElementToViewport(target, options = {}) {
    if (!target) {
        return;
    }

    const {
        margin = 12,
        fallbackTop = null,
        fallbackRight = null,
        fallbackBottom = null,
        fallbackLeft = null,
    } = options;

    const rect = target.getBoundingClientRect();
    if (!rect.width || !rect.height) {
        return;
    }

    const viewportWidth = window.innerWidth;
    const viewportHeight = window.innerHeight;
    const isFullyOffscreen = (
        rect.right < margin
        || rect.left > viewportWidth - margin
        || rect.bottom < margin
        || rect.top > viewportHeight - margin
    );

    if (isFullyOffscreen) {
        if (fallbackLeft !== null) {
            target.style.left = `${fallbackLeft}px`;
        }
        if (fallbackTop !== null) {
            target.style.top = `${fallbackTop}px`;
        }
        if (fallbackRight !== null) {
            target.style.right = `${fallbackRight}px`;
            target.style.left = "auto";
        }
        if (fallbackBottom !== null) {
            target.style.bottom = `${fallbackBottom}px`;
            target.style.top = "auto";
        }
        if (target === elements.captionBox && fallbackLeft === null) {
            target.style.left = "50%";
            target.style.bottom = `${fallbackBottom ?? 24}px`;
            target.style.top = "auto";
            target.style.right = "auto";
            target.style.transform = "translateX(-50%)";
        }
        return;
    }

    if (!target.style.left || !target.style.top) {
        return;
    }

    const maxLeft = Math.max(margin, viewportWidth - rect.width - margin);
    const maxTop = Math.max(margin, viewportHeight - rect.height - margin);
    const clampedLeft = Math.min(Math.max(rect.left, margin), maxLeft);
    const clampedTop = Math.min(Math.max(rect.top, margin), maxTop);

    target.style.left = `${clampedLeft}px`;
    target.style.top = `${clampedTop}px`;
    target.style.right = "auto";
    target.style.bottom = "auto";
    target.style.transform = "none";
}
