/** 회의 기록의 화자 목록. 화자를 눌러 이름을 붙이면 같은 화자의 모든 발화에 반영된다. */
import React, { useEffect, useRef, useState } from "react";
import { Check, Pencil, X } from "lucide-react";

export function SpeakerNamesBar({ onRename, speakers }) {
  const [editingLabel, setEditingLabel] = useState(null);
  const [draftName, setDraftName] = useState("");
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState(null);
  const inputRef = useRef(null);

  useEffect(() => {
    if (editingLabel) {
      inputRef.current?.focus();
      inputRef.current?.select();
    }
  }, [editingLabel]);

  function startEditing(item) {
    setError(null);
    setEditingLabel(item.speaker_label);
    setDraftName(item.custom_name ?? "");
  }

  function cancelEditing() {
    setEditingLabel(null);
    setDraftName("");
  }

  async function save(item) {
    const nextName = draftName.trim();
    if (nextName === (item.custom_name ?? "")) {
      cancelEditing();
      return;
    }
    try {
      setSaving(true);
      setError(null);
      await onRename({ speakerLabel: item.speaker_label, displayName: nextName });
      cancelEditing();
    } catch (nextError) {
      setError(nextError instanceof Error ? nextError.message : "화자 이름을 바꾸지 못했습니다.");
    } finally {
      setSaving(false);
    }
  }

  return (
    <div className="caps-speaker-bar">
      <div className="caps-speaker-bar-head">
        <span className="caps-speaker-bar-title">화자</span>
        <span className="caps-speaker-bar-hint">이름을 붙이면 이 회의 기록 전체에 반영돼요.</span>
      </div>
      <ul className="caps-speaker-list">
        {speakers.items.map((item) =>
          editingLabel === item.speaker_label ? (
            <li key={item.speaker_label} className="caps-speaker-chip editing">
              <form
                onSubmit={(event) => {
                  event.preventDefault();
                  void save(item);
                }}
              >
                <input
                  ref={inputRef}
                  aria-label={`${item.default_name} 이름`}
                  disabled={saving}
                  maxLength={speakers.max_name_length}
                  onChange={(event) => setDraftName(event.target.value)}
                  onKeyDown={(event) => {
                    if (event.key === "Escape") {
                      cancelEditing();
                    }
                  }}
                  placeholder={item.default_name}
                  value={draftName}
                />
                <button aria-label="저장" disabled={saving} type="submit">
                  <Check size={14} />
                </button>
                <button aria-label="취소" disabled={saving} onClick={cancelEditing} type="button">
                  <X size={14} />
                </button>
              </form>
            </li>
          ) : (
            <li key={item.speaker_label} className="caps-speaker-chip">
              <button
                aria-label={`${item.display_name} 이름 바꾸기`}
                onClick={() => startEditing(item)}
                type="button"
              >
                <strong>{item.display_name}</strong>
                {item.custom_name ? <span className="caps-speaker-default">({item.default_name})</span> : null}
                <span className="caps-speaker-count">· 발화 {item.utterance_count}</span>
                <Pencil aria-hidden="true" size={12} />
              </button>
            </li>
          ),
        )}
      </ul>
      {error ? <p className="caps-speaker-error" role="alert">{error}</p> : null}
    </div>
  );
}
