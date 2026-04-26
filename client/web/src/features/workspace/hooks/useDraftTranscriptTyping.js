/** draft transcript를 새로 받을 때 문장이 타이핑되듯 보이도록 화면용 상태를 만든다. */
import { useEffect, useMemo, useRef, useState } from "react";

const TYPING_INTERVAL_MS = 20;
const MIN_STEP = 2;
const MAX_STEP = 6;

function getTypingStep(text) {
  const length = text?.length ?? 0;
  if (length >= 120) {
    return MAX_STEP;
  }
  if (length >= 60) {
    return 4;
  }
  return MIN_STEP;
}

/**
 * backend는 draft row를 발화 단위로 저장하므로, frontend는 새 row가 생길 때만
 * 글자를 조금씩 풀어 보여주면 사용자가 "지금 쓰이고 있다"는 감각을 얻을 수 있다.
 */
export default function useDraftTranscriptTyping(rows) {
  const queueRef = useRef([]);
  const seenDraftIdsRef = useRef(new Set());
  const rowsRef = useRef(rows);
  const [visibleLengths, setVisibleLengths] = useState({});

  useEffect(() => {
    rowsRef.current = rows;
  }, [rows]);

  useEffect(() => {
    setVisibleLengths((current) => {
      const next = {};

      for (const row of rows) {
        if (!row.isDraft) {
          next[row.id] = row.text.length;
          continue;
        }

        if (!seenDraftIdsRef.current.has(row.id)) {
          seenDraftIdsRef.current.add(row.id);
          queueRef.current.push(row.id);
          next[row.id] = 0;
          continue;
        }

        next[row.id] = Math.min(current[row.id] ?? row.text.length, row.text.length);
      }

      return next;
    });
  }, [rows]);

  useEffect(() => {
    const timerId = window.setInterval(() => {
      const activeId = queueRef.current[0];
      if (!activeId) {
        return;
      }

      const activeRow = rowsRef.current.find((row) => row.id === activeId && row.isDraft);
      if (!activeRow) {
        queueRef.current.shift();
        return;
      }

      setVisibleLengths((current) => {
        const currentLength = current[activeId] ?? 0;
        const nextLength = Math.min(
          currentLength + getTypingStep(activeRow.text),
          activeRow.text.length,
        );

        if (nextLength >= activeRow.text.length) {
          queueRef.current.shift();
        }

        if (nextLength === currentLength) {
          return current;
        }

        return {
          ...current,
          [activeId]: nextLength,
        };
      });
    }, TYPING_INTERVAL_MS);

    return () => {
      window.clearInterval(timerId);
    };
  }, []);

  return useMemo(
    () => {
      const activeDraftId = queueRef.current[0] ?? null;

      return rows.flatMap((row) => {
        if (!row.isDraft) {
          return [{
            ...row,
            displayText: row.text,
            isTyping: false,
          }];
        }

        const visibleLength = visibleLengths[row.id] ?? 0;
        const isQueuedBehindActive =
          visibleLength === 0 && activeDraftId !== null && activeDraftId !== row.id;

        if (isQueuedBehindActive || visibleLength === 0) {
          return [];
        }

        return [{
          ...row,
          displayText: row.text.slice(0, visibleLength),
          isTyping: visibleLength < row.text.length,
        }];
      });
    },
    [rows, visibleLengths],
  );
}
