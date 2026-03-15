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
