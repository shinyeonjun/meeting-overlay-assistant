"""오디오 영역의 backend 서비스를 제공한다."""
from __future__ import annotations

import os
import tempfile
import wave
from pathlib import Path


def resolve_model_name(*, model_id: str, model_path: Path | None) -> str:
    """Moonshine 모델 이름 또는 경로를 반환한다."""

    return str(model_path) if model_path else model_id


def write_segment_to_temp_wave(
    *,
    raw_bytes: bytes,
    channels: int,
    sample_width_bytes: int,
    sample_rate_hz: int,
) -> str:
    """PCM 바이트를 임시 WAV 파일로 저장한다."""

    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as temp_file:
        temp_path = temp_file.name

    with wave.open(temp_path, "wb") as wav_file:
        wav_file.setnchannels(channels)
        wav_file.setsampwidth(sample_width_bytes)
        wav_file.setframerate(sample_rate_hz)
        wav_file.writeframes(raw_bytes)

    return temp_path


def cleanup_temp_wave(path: str) -> None:
    """임시 WAV 파일을 정리한다."""

    try:
        os.remove(path)
    except OSError:
        pass


def run_transcribe(*, audio_paths: list[str], model_name: str) -> list[str]:
    """Moonshine 전사 백엔드를 선택해 실행한다."""

    try:
        from moonshine_onnx import transcribe
    except ImportError:
        return run_transcribe_with_moonshine_voice(
            audio_paths=audio_paths,
            model_name=model_name,
        )

    results = transcribe(audio=audio_paths, model_name=model_name)
    return [str(item) for item in results]


def run_transcribe_with_moonshine_voice(
    *,
    audio_paths: list[str],
    model_name: str,
) -> list[str]:
    """moonshine_voice backend로 전사를 수행한다."""

    try:
        from moonshine_voice import Transcriber, get_model_for_language
        from moonshine_voice.moonshine_api import ModelArch, string_to_model_arch
    except ImportError as error:
        raise RuntimeError(
            "moonshine backend를 사용하려면 moonshine_onnx 또는 moonshine_voice 패키지를 설치해야 합니다."
        ) from error

    model_path, model_arch = resolve_moonshine_voice_model(
        model_name=model_name,
        get_model_for_language=get_model_for_language,
        string_to_model_arch=string_to_model_arch,
        model_arch_enum=ModelArch,
    )

    texts: list[str] = []
    with Transcriber(model_path=model_path, model_arch=model_arch) as transcriber:
        for audio_path in audio_paths:
            audio, sample_rate = load_wave_for_moonshine_voice(audio_path)
            transcript = transcriber.transcribe_without_streaming(
                audio_data=audio,
                sample_rate=sample_rate,
            )
            joined = " ".join(
                line.text.strip()
                for line in transcript.lines
                if line.text and line.text.strip()
            ).strip()
            texts.append(joined)
    return texts


def resolve_moonshine_voice_model(
    *,
    model_name: str,
    get_model_for_language,
    string_to_model_arch,
    model_arch_enum,
) -> tuple[str, object]:
    """moonshine_voice backend용 모델 경로/아키텍처를 찾는다."""

    candidate_path = Path(model_name)
    if candidate_path.exists():
        inferred_arch = infer_model_arch_from_name(
            candidate_path.name,
            string_to_model_arch=string_to_model_arch,
            model_arch_enum=model_arch_enum,
        )
        return str(candidate_path), inferred_arch

    normalized = model_name.split("/")[-1].strip().casefold()
    language = infer_language_code(normalized)
    wanted_arch = infer_model_arch_from_name(
        normalized,
        string_to_model_arch=string_to_model_arch,
        model_arch_enum=model_arch_enum,
    )
    return get_model_for_language(
        wanted_language=language,
        wanted_model_arch=wanted_arch,
    )


def infer_language_code(model_name: str) -> str:
    """모델 이름에서 언어 코드를 추정한다."""

    for language in ("ko", "ja", "en", "es", "ar", "vi", "uk", "zh"):
        if model_name.endswith(f"-{language}") or f"-{language}-" in model_name:
            return language
    return "ko"


def infer_model_arch_from_name(
    model_name: str,
    *,
    string_to_model_arch,
    model_arch_enum,
):
    """모델 이름에서 moonshine 아키텍처를 추정한다."""

    name = model_name.casefold()
    candidates = (
        "medium-streaming",
        "small-streaming",
        "base-streaming",
        "tiny-streaming",
        "base",
        "tiny",
    )
    for candidate in candidates:
        if candidate in name:
            return string_to_model_arch(candidate)
    return model_arch_enum.TINY


def load_wave_for_moonshine_voice(audio_path: str) -> tuple[list[float], int]:
    """moonshine_voice backend용 WAV 파일을 로드한다."""

    with wave.open(audio_path, "rb") as wav_file:
        channels = wav_file.getnchannels()
        sample_width = wav_file.getsampwidth()
        sample_rate = wav_file.getframerate()
        frame_count = wav_file.getnframes()
        raw_bytes = wav_file.readframes(frame_count)

    if sample_width != 2:
        raise RuntimeError(
            "moonshine_voice backend는 현재 16-bit PCM WAV 입력만 지원합니다."
        )

    np = np_module()
    pcm = np.frombuffer(raw_bytes, dtype=np.int16).astype(np.float32)
    if channels > 1:
        pcm = pcm.reshape(-1, channels).mean(axis=1)
    audio = np.clip(pcm / 32768.0, -1.0, 1.0)
    return audio.tolist(), sample_rate


def np_module():
    """numpy 모듈을 늦게 로드한다."""

    import numpy as np

    return np
