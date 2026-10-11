import { elements } from "../../dom/elements.js";
import {
    closeWorkspace,
    openWorkspace,
} from "./ui-workspace-controller.js";
import { sendUIRects } from "./ui-bridge-controller.js";

const POSITION_KEY = "caps-overlay-positions";

export function setupDraggableLayout() {
    restorePositions();
    clampFloatingLayout();

    const captionHeader = elements.captionHeader;
    if (captionHeader) {
        makeDraggable(captionHeader, elements.captionBox, "captionBox");
    }

    const workspaceHeader = elements.workspaceHeader;
    if (workspaceHeader) {
        makeDraggable(workspaceHeader, elements.workspace, "workspace");
    }

    setupFabDrag();
}

/**
 * 드래그 공통 흐름: 현재 위치를 고정하고, 마우스 이동을 target의 left/top에 반영한다.
 * threshold를 넘게 움직이기 전까지는 드래그로 보지 않는다(클릭과 구분할 때 쓴다).
 */
function startDrag(target, event, { threshold = 0, resetTransform = false, onEnd }) {
    event.preventDefault();

    const rect = target.getBoundingClientRect();
    target.style.left = `${rect.left}px`;
    target.style.top = `${rect.top}px`;
    target.style.right = "auto";
    target.style.bottom = "auto";
    if (resetTransform) {
        target.style.transform = "none";
    }

    const startX = event.clientX;
    const startY = event.clientY;
    const originX = rect.left;
    const originY = rect.top;
    let dragged = false;

    const onMove = (moveEvent) => {
        const deltaX = moveEvent.clientX - startX;
        const deltaY = moveEvent.clientY - startY;
        if (!dragged && (Math.abs(deltaX) > threshold || Math.abs(deltaY) > threshold)) {
            dragged = true;
        }
        if (!dragged) {
            return;
        }
        target.style.left = `${originX + deltaX}px`;
        target.style.top = `${originY + deltaY}px`;
    };

    const onUp = () => {
        document.removeEventListener("mousemove", onMove);
        document.removeEventListener("mouseup", onUp);
        onEnd?.(dragged);
    };

    document.addEventListener("mousemove", onMove);
    document.addEventListener("mouseup", onUp);
}

function makeDraggable(handle, target, storageKey) {
    handle.addEventListener("mousedown", (event) => {
        if (event.target.closest("button")) {
            return;
        }
        startDrag(target, event, {
            resetTransform: true,
            onEnd: () => {
                sendUIRects();
                if (storageKey) {
                    savePosition(storageKey, target);
                }
            },
        });
    });

    handle.style.cursor = "grab";
    handle.addEventListener("mousedown", () => {
        handle.style.cursor = "grabbing";
    });
    document.addEventListener("mouseup", () => {
        handle.style.cursor = "grab";
    });
}

function setupFabDrag() {
    const fab = elements.togglePanel;
    if (!fab) {
        return;
    }

    fab.addEventListener("mousedown", (event) => {
        startDrag(fab, event, {
            threshold: 5,
            onEnd: (dragged) => {
                if (!dragged) {
                    if (elements.workspace.classList.contains("collapsed")) {
                        openWorkspace();
                    } else {
                        closeWorkspace();
                    }
                }
                sendUIRects();
            },
        });
    });
}

function savePosition(key, target) {
    try {
        const stored = JSON.parse(localStorage.getItem(POSITION_KEY) || "{}");
        stored[key] = {
            left: target.style.left,
            top: target.style.top,
        };
        localStorage.setItem(POSITION_KEY, JSON.stringify(stored));
    } catch {
        // localStorage를 사용할 수 없으면 무시한다.
    }
}

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
    } catch {
        // localStorage를 사용할 수 없으면 무시한다.
    }
}

export function clampFloatingLayout() {
    clampElementToViewport(elements.captionBox, {
        margin: 12,
        fallbackBottom: 24,
        fallbackLeft: null,
    });
    clampElementToViewport(elements.workspace, {
        margin: 12,
        fallbackTop: 24,
        fallbackRight: 24,
    });
    clampElementToViewport(elements.togglePanel, {
        margin: 12,
        fallbackBottom: 20,
        fallbackRight: 20,
    });
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
