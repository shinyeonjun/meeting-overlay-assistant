/** 워크스페이스 녹음 플레이어 UI를 분리한 컴포넌트다. */
import React from "react";
import { Pause, Play } from "lucide-react";

function formatAudioClock(totalSeconds) {
  const safeSeconds = Number.isFinite(totalSeconds) ? Math.max(0, Math.floor(totalSeconds)) : 0;
  const hours = Math.floor(safeSeconds / 3600);
  const minutes = Math.floor((safeSeconds % 3600) / 60);
  const seconds = safeSeconds % 60;

  if (hours > 0) {
    return `${String(hours).padStart(2, "0")}:${String(minutes).padStart(2, "0")}:${String(seconds).padStart(2, "0")}`;
  }
  return `${String(minutes).padStart(2, "0")}:${String(seconds).padStart(2, "0")}`;
}

export default function WorkspaceAudioPlayer({
  audioCurrentTime,
  audioDuration,
  audioReady,
  audioRef,
  loadingAudio,
  onSeekAudio,
  onToggleAudioPlayback,
  playingAudio,
}) {
  const sliderDisabled = !audioReady || audioDuration <= 0;
  const showPauseButton = playingAudio || loadingAudio;

  return (
    <div className="caps-audio-player">
      <audio ref={audioRef} hidden preload="metadata" />

      <div className="caps-audio-player-main">
        <button
          aria-label={showPauseButton ? "재생 멈추기" : "재생 시작"}
          className="caps-audio-player-button"
          onClick={onToggleAudioPlayback}
          type="button"
        >
          {showPauseButton ? <Pause size={16} /> : <Play size={16} />}
        </button>

        <div className="caps-audio-player-copy">
          <strong>회의 녹음</strong>
        </div>
      </div>

      <div className="caps-audio-player-track">
        <span className="caps-audio-player-time">{formatAudioClock(audioCurrentTime)}</span>
        <input
          className="caps-audio-player-slider"
          disabled={sliderDisabled}
          max={audioDuration > 0 ? audioDuration : 0}
          min="0"
          onChange={onSeekAudio}
          step="0.1"
          type="range"
          value={audioDuration > 0 ? Math.min(audioCurrentTime, audioDuration) : 0}
        />
        <span className="caps-audio-player-time">
          {audioReady && audioDuration > 0 ? formatAudioClock(audioDuration) : "--:--"}
        </span>
      </div>
    </div>
  );
}
