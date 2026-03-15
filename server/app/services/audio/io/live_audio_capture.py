"""실시간 마이크/시스템 오디오 캡처 유틸리티."""

from __future__ import annotations

from collections.abc import Iterator
from dataclasses import dataclass
import logging
from typing import Any, Protocol
import warnings


logger = logging.getLogger(__name__)


class AudioCaptureStream(Protocol):
    """실시간 오디오 청크를 순회하는 스트림 인터페이스."""

    def iter_chunks(self) -> Iterator[bytes]:
        """PCM 청크를 순회한다."""


@dataclass(frozen=True)
class LiveAudioCaptureConfig:
    """실시간 오디오 캡처 설정."""

    source: str
    sample_rate_hz: int = 16000
    channels: int = 1
    chunk_duration_ms: int = 1000
    device_name: str | None = None

    @property
    def frames_per_chunk(self) -> int:
        """청크 하나에 포함되는 프레임 수를 반환한다."""
        return max(int(self.sample_rate_hz * (self.chunk_duration_ms / 1000)), 1)


class MicrophoneAudioCapture(AudioCaptureStream):
    """sounddevice를 이용한 마이크 캡처."""

    def __init__(self, config: LiveAudioCaptureConfig) -> None:
        self._config = config

    def iter_chunks(self) -> Iterator[bytes]:
        sounddevice = _import_sounddevice()
        selected_device = select_microphone_input_device(sounddevice, self._config.device_name)
        selected_device_name = _resolve_sounddevice_name(sounddevice, selected_device)
        logger.info(
            "마이크 입력 장치 선택: requested=%s selected=%s",
            self._config.device_name,
            selected_device_name,
        )

        with sounddevice.InputStream(
            samplerate=self._config.sample_rate_hz,
            channels=self._config.channels,
            dtype="float32",
            blocksize=self._config.frames_per_chunk,
            device=selected_device,
        ) as stream:
            while True:
                frames, _overflowed = stream.read(self._config.frames_per_chunk)
                yield float32_audio_to_pcm16_bytes(frames)


class SystemAudioLoopbackCapture(AudioCaptureStream):
    """soundcard를 이용한 시스템 오디오 loopback 캡처."""

    def __init__(self, config: LiveAudioCaptureConfig) -> None:
        self._config = config

    def iter_chunks(self) -> Iterator[bytes]:
        soundcard = _import_soundcard()
        microphone = select_system_loopback_microphone(soundcard, self._config.device_name)

        with microphone.recorder(
            samplerate=self._config.sample_rate_hz,
            channels=self._config.channels,
            blocksize=self._config.frames_per_chunk,
        ) as recorder:
            while True:
                with warnings.catch_warnings(record=True) as caught_warnings:
                    warnings.simplefilter("always")
                    frames = recorder.record(numframes=self._config.frames_per_chunk)
                if _has_data_discontinuity_warning(caught_warnings):
                    continue
                yield float32_audio_to_pcm16_bytes(frames)


def create_live_audio_capture(config: LiveAudioCaptureConfig) -> AudioCaptureStream:
    """설정에 맞는 실시간 오디오 캡처 객체를 생성한다."""
    if config.source == "mic":
        return MicrophoneAudioCapture(config)
    if config.source == "system_audio":
        return SystemAudioLoopbackCapture(config)
    raise ValueError(f"지원하지 않는 live audio source입니다: {config.source}")


def resolve_live_capture_device_label(config: LiveAudioCaptureConfig) -> str:
    """실제로 사용할 입력 장치명을 문자열로 반환한다."""
    if config.source == "mic":
        sounddevice = _import_sounddevice()
        selected_device = select_microphone_input_device(sounddevice, config.device_name)
        return _resolve_sounddevice_name(sounddevice, selected_device)

    if config.source == "system_audio":
        soundcard = _import_soundcard()
        microphone = select_system_loopback_microphone(soundcard, config.device_name)
        return str(getattr(microphone, "name", "system-loopback"))

    return "unknown"


def float32_audio_to_pcm16_bytes(frames: Any) -> bytes:
    """float32 오디오 프레임을 16-bit PCM 바이트로 변환한다."""
    np = _import_numpy()
    array = np.asarray(frames, dtype=np.float32)
    if array.ndim == 2:
        array = array.mean(axis=1)
    array = np.clip(array, -1.0, 1.0)
    pcm16 = (array * 32767.0).astype(np.int16)
    return pcm16.tobytes()


def select_system_loopback_microphone(soundcard_module: Any, device_name: str | None):
    """이름 또는 기본 loopback 마이크를 선택한다."""
    if device_name:
        for microphone in soundcard_module.all_microphones(include_loopback=True):
            if getattr(microphone, "isloopback", False) and microphone.name == device_name:
                return microphone
        raise ValueError(f"지정한 시스템 오디오 장치를 찾을 수 없습니다: {device_name}")

    for microphone in soundcard_module.all_microphones(include_loopback=True):
        if getattr(microphone, "isloopback", False):
            return microphone
    default_speaker = soundcard_module.default_speaker()
    if default_speaker is None:
        raise ValueError("기본 시스템 오디오 장치를 찾을 수 없습니다.")
    return soundcard_module.get_microphone(str(default_speaker.id), include_loopback=True)


def list_microphone_devices() -> list[str]:
    """사용 가능한 마이크 장치 이름을 반환한다."""
    sounddevice = _import_sounddevice()
    devices = []
    for device in sounddevice.query_devices():
        if device.get("max_input_channels", 0) > 0:
            devices.append(str(device.get("name")))
    return devices


def select_microphone_input_device(sounddevice_module: Any, device_name: str | None):
    """마이크 입력 장치를 선택한다.

    우선순위:
    1) 명시적 device_name
    2) 기본 입력 장치(루프백 계열이 아니면)
    3) 루프백으로 보이지 않는 첫 입력 장치
    4) 첫 입력 장치
    """
    devices = list(sounddevice_module.query_devices())
    input_candidates = [
        (index, str(device.get("name", "")))
        for index, device in enumerate(devices)
        if device.get("max_input_channels", 0) > 0
    ]
    if not input_candidates:
        raise ValueError("사용 가능한 마이크 입력 장치를 찾을 수 없습니다.")

    if device_name:
        normalized_target = device_name.strip().casefold()
        for index, name in input_candidates:
            if name.strip().casefold() == normalized_target:
                return index
        raise ValueError(f"지정한 마이크 장치를 찾을 수 없습니다: {device_name}")

    default_input_index = _resolve_default_input_index(sounddevice_module)
    if default_input_index is not None:
        default_name = _resolve_sounddevice_name(sounddevice_module, default_input_index)
        if not _is_likely_loopback_input_device_name(default_name):
            return default_input_index

    non_loopback_candidate = next(
        (index for index, name in input_candidates if not _is_likely_loopback_input_device_name(name)),
        None,
    )
    if non_loopback_candidate is not None:
        return non_loopback_candidate

    return input_candidates[0][0]


def list_system_audio_devices() -> list[str]:
    """사용 가능한 시스템 오디오 장치 이름을 반환한다."""
    soundcard = _import_soundcard()
    return [
        microphone.name
        for microphone in soundcard.all_microphones(include_loopback=True)
        if getattr(microphone, "isloopback", False)
    ]


def _has_data_discontinuity_warning(caught_warnings: list[warnings.WarningMessage]) -> bool:
    for warning in caught_warnings:
        if "data discontinuity in recording" in str(warning.message).casefold():
            return True
    return False


def _resolve_default_input_index(sounddevice_module: Any) -> int | None:
    default_device = getattr(sounddevice_module, "default", None)
    if default_device is None:
        return None
    default_value = getattr(default_device, "device", None)
    if isinstance(default_value, (tuple, list)):
        if not default_value:
            return None
        default_input = default_value[0]
    else:
        default_input = default_value

    try:
        default_input = int(default_input)
    except (TypeError, ValueError):
        return None

    if default_input < 0:
        return None
    return default_input


def _resolve_sounddevice_name(sounddevice_module: Any, device_index: int) -> str:
    try:
        device = sounddevice_module.query_devices(device_index)
    except Exception:
        return f"index={device_index}"
    return str(device.get("name", f"index={device_index}"))


def _is_likely_loopback_input_device_name(name: str) -> bool:
    normalized = name.casefold()
    loopback_keywords = (
        "stereo mix",
        "스테레오 믹스",
        "loopback",
        "what u hear",
        "wave out",
        "monitor",
        "output",
        "출력",
        "speaker",
        "스피커",
        "virtual",
        "vb-audio",
        "cable output",
    )
    return any(keyword in normalized for keyword in loopback_keywords)


def _import_numpy():
    import numpy as np

    return np


def _import_sounddevice():
    try:
        import sounddevice
    except ImportError as error:
        raise RuntimeError(
            "마이크 캡처를 사용하려면 sounddevice 패키지가 필요합니다. "
            "pip install sounddevice"
        ) from error
    return sounddevice


def _import_soundcard():
    try:
        import soundcard
    except ImportError as error:
        raise RuntimeError(
            "시스템 오디오 캡처를 사용하려면 soundcard 패키지가 필요합니다. "
            "pip install soundcard"
        ) from error
    return soundcard
