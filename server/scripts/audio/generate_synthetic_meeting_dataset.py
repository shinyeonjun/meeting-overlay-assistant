"""기존 한국어 샘플 음성을 이용해 synthetic meeting WAV 세트를 생성한다."""

from __future__ import annotations

import argparse
import json
import math
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np
import soundfile as sf
from scipy.signal import butter, lfilter, resample_poly


PROJECT_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_SOURCE_WAV = PROJECT_ROOT / "tests" / "fixtures" / "video" / "test_16k_mono_15s.wav"
DEFAULT_SOURCE_TEXT = PROJECT_ROOT / "tests" / "fixtures" / "video" / "test.txt"
DEFAULT_OUTPUT_DIR = PROJECT_ROOT / "tests" / "fixtures" / "video" / "synthetic_meeting"


@dataclass(frozen=True)
class SpeakerProfile:
    """화자별 음색/속도 변형 프로필."""

    speaker_id: str
    speed_ratio: float
    gain_db: float
    lowpass_hz: float | None = None
    highpass_hz: float | None = None


@dataclass(frozen=True)
class ScenarioTurn:
    """합성 회의의 단일 턴."""

    speaker_id: str
    segment_index: int
    gap_ms: int = 260
    overlap_ms: int = 0


@dataclass(frozen=True)
class ScenarioDefinition:
    """합성 회의 시나리오."""

    name: str
    title: str
    description: str
    noise_level: float
    hum_level: float
    turns: tuple[ScenarioTurn, ...]


SPEAKER_PROFILES: dict[str, SpeakerProfile] = {
    "speaker_a": SpeakerProfile(
        speaker_id="speaker_a",
        speed_ratio=1.00,
        gain_db=0.0,
        lowpass_hz=None,
        highpass_hz=90.0,
    ),
    "speaker_b": SpeakerProfile(
        speaker_id="speaker_b",
        speed_ratio=1.07,
        gain_db=-1.2,
        lowpass_hz=5400.0,
        highpass_hz=150.0,
    ),
    "speaker_c": SpeakerProfile(
        speaker_id="speaker_c",
        speed_ratio=0.94,
        gain_db=0.8,
        lowpass_hz=3800.0,
        highpass_hz=70.0,
    ),
}


SCENARIOS: tuple[ScenarioDefinition, ...] = (
    ScenarioDefinition(
        name="synthetic_meeting_easy",
        title="Synthetic Meeting Easy",
        description="2화자가 천천히 교대하는 쉬운 회의 샘플",
        noise_level=0.0020,
        hum_level=0.0007,
        turns=(
            ScenarioTurn("speaker_a", 0, gap_ms=380),
            ScenarioTurn("speaker_b", 1, gap_ms=340),
            ScenarioTurn("speaker_a", 2, gap_ms=300),
            ScenarioTurn("speaker_b", 3, gap_ms=360),
            ScenarioTurn("speaker_a", 4, gap_ms=260),
            ScenarioTurn("speaker_b", 5, gap_ms=300),
        ),
    ),
    ScenarioDefinition(
        name="synthetic_meeting_normal",
        title="Synthetic Meeting Normal",
        description="3화자가 빠르게 턴테이킹하는 일반 회의 샘플",
        noise_level=0.0035,
        hum_level=0.0010,
        turns=(
            ScenarioTurn("speaker_a", 0, gap_ms=240),
            ScenarioTurn("speaker_b", 1, gap_ms=180),
            ScenarioTurn("speaker_c", 2, gap_ms=140),
            ScenarioTurn("speaker_a", 3, gap_ms=220),
            ScenarioTurn("speaker_b", 4, gap_ms=120, overlap_ms=80),
            ScenarioTurn("speaker_c", 5, gap_ms=180),
            ScenarioTurn("speaker_a", 1, gap_ms=160),
            ScenarioTurn("speaker_b", 4, gap_ms=240),
        ),
    ),
    ScenarioDefinition(
        name="synthetic_meeting_hard",
        title="Synthetic Meeting Hard",
        description="겹침 발화와 짧은 간격이 섞인 어려운 회의 샘플",
        noise_level=0.0050,
        hum_level=0.0012,
        turns=(
            ScenarioTurn("speaker_a", 0, gap_ms=120),
            ScenarioTurn("speaker_b", 1, gap_ms=80, overlap_ms=140),
            ScenarioTurn("speaker_c", 2, gap_ms=100),
            ScenarioTurn("speaker_a", 3, gap_ms=90, overlap_ms=120),
            ScenarioTurn("speaker_b", 4, gap_ms=100),
            ScenarioTurn("speaker_c", 5, gap_ms=80, overlap_ms=180),
            ScenarioTurn("speaker_a", 2, gap_ms=120),
            ScenarioTurn("speaker_b", 0, gap_ms=140),
            ScenarioTurn("speaker_c", 4, gap_ms=100),
        ),
    ),
)


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="synthetic meeting WAV 세트를 생성합니다.")
    parser.add_argument("--source-wav", default=str(DEFAULT_SOURCE_WAV))
    parser.add_argument("--source-reference", default=str(DEFAULT_SOURCE_TEXT))
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR))
    parser.add_argument("--sample-rate", type=int, default=16000)
    parser.add_argument("--seed", type=int, default=20260317)
    return parser


def _read_audio(path: Path, expected_sample_rate: int) -> np.ndarray:
    audio, sample_rate = sf.read(path, dtype="float32")
    if sample_rate != expected_sample_rate:
        raise ValueError(f"샘플레이트가 다릅니다. expected={expected_sample_rate} actual={sample_rate}")
    if audio.ndim == 2:
        audio = np.mean(audio, axis=1)
    return np.asarray(audio, dtype=np.float32)


def _split_reference_text(text: str, *, min_parts: int = 6) -> list[str]:
    normalized = re.sub(r"\s+", " ", text.strip())
    if not normalized:
        raise ValueError("reference text가 비어 있습니다.")

    sentence_like = [
        item.strip()
        for item in re.split(r"(?<=[.!?])\s+|(?<=요)\s+|(?<=다)\s+", normalized)
        if item.strip()
    ]
    parts: list[str] = []
    for sentence in sentence_like:
        words = sentence.split()
        if len(words) <= 5:
            parts.append(sentence)
            continue
        chunk: list[str] = []
        for word in words:
            chunk.append(word)
            compact_length = len(" ".join(chunk))
            if compact_length >= 18:
                parts.append(" ".join(chunk).strip())
                chunk = []
        if chunk:
            parts.append(" ".join(chunk).strip())

    while len(parts) < min_parts:
        longest_index = max(range(len(parts)), key=lambda index: len(parts[index]))
        words = parts[longest_index].split()
        if len(words) < 4:
            break
        pivot = math.ceil(len(words) / 2)
        parts[longest_index : longest_index + 1] = [
            " ".join(words[:pivot]).strip(),
            " ".join(words[pivot:]).strip(),
        ]

    return [part for part in parts if part]


def _slice_audio_by_text(audio: np.ndarray, text_parts: list[str]) -> list[np.ndarray]:
    weights = np.array([max(len(re.sub(r"\s+", "", part)), 1) for part in text_parts], dtype=np.float64)
    weights = weights / weights.sum()
    total_samples = len(audio)
    boundaries = [0]
    consumed = 0
    for index, weight in enumerate(weights[:-1], start=1):
        segment_length = int(round(total_samples * weight))
        consumed += segment_length
        boundaries.append(min(consumed, total_samples))
    boundaries.append(total_samples)

    segments: list[np.ndarray] = []
    for start, end in zip(boundaries[:-1], boundaries[1:], strict=True):
        clip = np.copy(audio[start:end])
        clip = _trim_silence(clip)
        if clip.size == 0:
            clip = np.zeros(1, dtype=np.float32)
        segments.append(clip.astype(np.float32))
    return segments


def _trim_silence(audio: np.ndarray, *, threshold: float = 0.01) -> np.ndarray:
    if audio.size == 0:
        return audio
    active = np.flatnonzero(np.abs(audio) >= threshold)
    if active.size == 0:
        return audio
    start = max(int(active[0]) - 200, 0)
    end = min(int(active[-1]) + 200, audio.size - 1)
    return audio[start : end + 1]


def _apply_gain(audio: np.ndarray, gain_db: float) -> np.ndarray:
    gain = float(10 ** (gain_db / 20.0))
    return (audio * gain).astype(np.float32)


def _apply_speed(audio: np.ndarray, speed_ratio: float) -> np.ndarray:
    if abs(speed_ratio - 1.0) < 1e-6:
        return audio.astype(np.float32)
    denominator = 100
    numerator = max(int(round(speed_ratio * denominator)), 1)
    transformed = resample_poly(audio, up=denominator, down=numerator)
    return transformed.astype(np.float32)


def _apply_filter(audio: np.ndarray, *, sample_rate: int, lowpass_hz: float | None, highpass_hz: float | None) -> np.ndarray:
    filtered = audio.astype(np.float32)
    nyquist = sample_rate / 2
    if highpass_hz is not None and 0 < highpass_hz < nyquist:
        b, a = butter(2, highpass_hz / nyquist, btype="highpass")
        filtered = lfilter(b, a, filtered).astype(np.float32)
    if lowpass_hz is not None and 0 < lowpass_hz < nyquist:
        b, a = butter(2, lowpass_hz / nyquist, btype="lowpass")
        filtered = lfilter(b, a, filtered).astype(np.float32)
    return filtered


def _build_speaker_variant(audio: np.ndarray, profile: SpeakerProfile, *, sample_rate: int) -> np.ndarray:
    transformed = _apply_speed(audio, profile.speed_ratio)
    transformed = _apply_filter(
        transformed,
        sample_rate=sample_rate,
        lowpass_hz=profile.lowpass_hz,
        highpass_hz=profile.highpass_hz,
    )
    transformed = _apply_gain(transformed, profile.gain_db)
    return transformed.astype(np.float32)


def _generate_room_noise(length: int, *, rng: np.random.Generator, noise_level: float, hum_level: float, sample_rate: int) -> np.ndarray:
    if length <= 0:
        return np.zeros(0, dtype=np.float32)
    white = rng.normal(0.0, noise_level, length).astype(np.float32)
    time_axis = np.arange(length, dtype=np.float32) / sample_rate
    hum = hum_level * np.sin(2 * np.pi * 60.0 * time_axis, dtype=np.float32)
    air = (hum_level * 0.6) * np.sin(2 * np.pi * 180.0 * time_axis, dtype=np.float32)
    return (white + hum + air).astype(np.float32)


def _mix_scenario(
    *,
    scenario: ScenarioDefinition,
    speaker_audio_bank: dict[str, list[np.ndarray]],
    text_parts: list[str],
    sample_rate: int,
    rng: np.random.Generator,
) -> tuple[np.ndarray, list[dict[str, Any]], str]:
    timeline_ms = 0
    rendered_turns: list[dict[str, Any]] = []
    clips: list[tuple[int, np.ndarray]] = []

    for turn in scenario.turns:
        clip = np.copy(speaker_audio_bank[turn.speaker_id][turn.segment_index])
        if rendered_turns:
            timeline_ms += max(turn.gap_ms - turn.overlap_ms, 0)
            if turn.overlap_ms > 0:
                timeline_ms = max(timeline_ms - turn.overlap_ms, 0)
        start_sample = int(sample_rate * (timeline_ms / 1000.0))
        end_sample = start_sample + len(clip)
        clips.append((start_sample, clip))
        rendered_turns.append(
            {
                "speaker_id": turn.speaker_id,
                "segment_index": turn.segment_index,
                "start_ms": round((start_sample / sample_rate) * 1000),
                "end_ms": round((end_sample / sample_rate) * 1000),
                "text": text_parts[turn.segment_index],
            }
        )
        timeline_ms = round((end_sample / sample_rate) * 1000)

    total_length = max(start + len(clip) for start, clip in clips) + int(sample_rate * 1.0)
    mixed = _generate_room_noise(
        total_length,
        rng=rng,
        noise_level=scenario.noise_level,
        hum_level=scenario.hum_level,
        sample_rate=sample_rate,
    )
    for start, clip in clips:
        end = start + len(clip)
        mixed[start:end] += clip

    peak = float(np.max(np.abs(mixed))) if mixed.size else 1.0
    if peak > 0.95:
        mixed = mixed * (0.95 / peak)
    transcript = " ".join(turn["text"] for turn in rendered_turns).strip()
    return mixed.astype(np.float32), rendered_turns, transcript


def _write_outputs(
    *,
    output_dir: Path,
    scenario: ScenarioDefinition,
    audio: np.ndarray,
    rendered_turns: list[dict[str, Any]],
    transcript: str,
    sample_rate: int,
) -> dict[str, Any]:
    output_dir.mkdir(parents=True, exist_ok=True)
    wav_path = output_dir / f"{scenario.name}.wav"
    reference_path = output_dir / f"{scenario.name}.txt"
    metadata_path = output_dir / f"{scenario.name}.json"

    sf.write(wav_path, audio, sample_rate, subtype="PCM_16")
    reference_path.write_text(transcript, encoding="utf-8")
    metadata = {
        "name": scenario.name,
        "title": scenario.title,
        "description": scenario.description,
        "wav_path": wav_path.name,
        "reference_file": reference_path.name,
        "turns": rendered_turns,
    }
    metadata_path.write_text(json.dumps(metadata, ensure_ascii=False, indent=2), encoding="utf-8")
    return metadata


def _write_dataset_manifest(output_dir: Path, items: list[dict[str, Any]]) -> None:
    dataset_path = output_dir / "synthetic_meeting.dataset.json"
    payload = {
        "default_threshold_profile": "system_audio_default",
        "samples": [
            {
                "name": item["name"],
                "wav_path": item["wav_path"],
                "source": "system_audio",
                "reference_file": item["reference_file"],
            }
            for item in items
        ],
    }
    dataset_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def main() -> int:
    parser = _build_parser()
    args = parser.parse_args()

    source_wav = Path(args.source_wav).resolve()
    source_reference = Path(args.source_reference).resolve()
    output_dir = Path(args.output_dir).resolve()

    audio = _read_audio(source_wav, args.sample_rate)
    text = source_reference.read_text(encoding="utf-8").strip()
    text_parts = _split_reference_text(text, min_parts=6)
    audio_segments = _slice_audio_by_text(audio, text_parts)

    speaker_audio_bank = {
        speaker_id: [
            _build_speaker_variant(segment, profile, sample_rate=args.sample_rate)
            for segment in audio_segments
        ]
        for speaker_id, profile in SPEAKER_PROFILES.items()
    }

    rng = np.random.default_rng(args.seed)
    written_items: list[dict[str, Any]] = []
    for scenario in SCENARIOS:
        rendered_audio, rendered_turns, transcript = _mix_scenario(
            scenario=scenario,
            speaker_audio_bank=speaker_audio_bank,
            text_parts=text_parts,
            sample_rate=args.sample_rate,
            rng=rng,
        )
        metadata = _write_outputs(
            output_dir=output_dir,
            scenario=scenario,
            audio=rendered_audio,
            rendered_turns=rendered_turns,
            transcript=transcript,
            sample_rate=args.sample_rate,
        )
        written_items.append(metadata)

    _write_dataset_manifest(output_dir, written_items)
    print(f"output_dir={output_dir}")
    for item in written_items:
        print(f"- {item['name']}: {item['wav_path']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
