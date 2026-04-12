const FLASH_DURATION_MS = 3000;
const flashTimers = new WeakMap();

export function setStatus(element, text, tone) {
    if (!element) {
        return;
    }
    element.textContent = text;
    element.className = `badge ${tone}`;
}

export function flashStatus(element, text, tone = "error") {
    const previousText = element.textContent;
    const previousClass = element.className;

    setStatus(element, text, tone);

    const existingTimer = flashTimers.get(element);
    if (existingTimer) {
        clearTimeout(existingTimer);
    }

    flashTimers.set(
        element,
        setTimeout(() => {
            element.textContent = previousText;
            element.className = previousClass;
            flashTimers.delete(element);
        }, FLASH_DURATION_MS),
    );
}
