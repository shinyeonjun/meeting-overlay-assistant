"""별도 venv에서 pyannote diarization을 수행하는 worker."""

from __future__ import annotations

import argparse
from array import array
import json
from pathlib import Path
import sys
import wave


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="pyannote diarization worker")
    parser.add_argument("--audio-path", required=True)
    parser.add_argument("--model-id", required=True)
    parser.add_argument("--auth-token", required=True)
    parser.add_argument("--device", default="cpu")
    return parser.parse_args()


def main() -> None:
    args = parse_args()

    import torch
    from pyannote.audio import Pipeline

    waveform_input = _read_waveform_input(Path(args.audio_path), torch)

    try:
        pipeline = Pipeline.from_pretrained(args.model_id, token=args.auth_token)
    except TypeError:
        pipeline = Pipeline.from_pretrained(args.model_id, use_auth_token=args.auth_token)

    if args.device != "cpu":
        pipeline.to(torch.device(args.device))

    diarization_result = pipeline(waveform_input)
    annotation = _extract_annotation(diarization_result)
    segments = [
        {
            "speaker_label": str(speaker_label),
            "start_ms": int(float(turn.start) * 1000),
            "end_ms": int(float(turn.end) * 1000),
        }
        for turn, _, speaker_label in annotation.itertracks(yield_label=True)
    ]
    json.dump({"segments": segments}, sys.stdout, ensure_ascii=False)


def _read_waveform_input(path: Path, torch_module) -> dict[str, object]:  # noqa: ANN001
    with wave.open(str(path), "rb") as wav_file:
        channels = wav_file.getnchannels()
        sample_width_bytes = wav_file.getsampwidth()
        sample_rate_hz = wav_file.getframerate()
        raw_bytes = wav_file.readframes(wav_file.getnframes())

    if sample_width_bytes != 2:
        raise ValueError("pyannote worker는 현재 16-bit PCM WAV만 지원합니다.")

    samples = array("h")
    samples.frombytes(raw_bytes)
    waveform = torch_module.tensor(samples, dtype=torch_module.float32) / 32768.0
    if channels > 1:
        waveform = waveform.reshape(-1, channels).transpose(0, 1)
    else:
        waveform = waveform.unsqueeze(0)

    return {
        "waveform": waveform,
        "sample_rate": sample_rate_hz,
    }


def _extract_annotation(diarization_result):  # noqa: ANN001
    if hasattr(diarization_result, "exclusive_speaker_diarization"):
        return diarization_result.exclusive_speaker_diarization
    if hasattr(diarization_result, "speaker_diarization"):
        return diarization_result.speaker_diarization
    return diarization_result


if __name__ == "__main__":
    main()
