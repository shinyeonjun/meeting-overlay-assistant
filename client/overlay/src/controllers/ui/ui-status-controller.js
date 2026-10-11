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
    const flashedText = element.textContent;
    const flashedClass = element.className;

    const existingTimer = flashTimers.get(element);
    if (existingTimer) {
        clearTimeout(existingTimer);
    }

    flashTimers.set(
        element,
        setTimeout(() => {
            // 그 사이 다른 상태로 바뀌었다면 오래된 값으로 덮어쓰지 않는다.
            if (element.textContent === flashedText && element.className === flashedClass) {
                element.textContent = previousText;
                element.className = previousClass;
            }
            flashTimers.delete(element);
        }, FLASH_DURATION_MS),
    );
}
