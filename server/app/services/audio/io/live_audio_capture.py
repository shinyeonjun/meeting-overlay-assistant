"""실시간 마이크, 시스템 오디오 캡처 유틸리티."""

from __future__ import annotations

from collections.abc import Iterator
from dataclasses import dataclass
import logging
from typing import Any, Protocol
import warnings

from server.app.services.audio.io.live_audio_capture_helpers import (
    float32_audio_to_pcm16_bytes as convert_float32_audio_to_pcm16_bytes,
    has_data_discontinuity_warning,
    import_soundcard,
    import_sounddevice,
    is_likely_loopback_input_device_name,
    list_microphone_devices as list_available_microphone_devices,
    list_system_audio_devices as list_available_system_audio_devices,
    resolve_default_input_index,
    resolve_sounddevice_name,
    select_microphone_input_device as choose_microphone_input_device,
    select_system_loopback_microphone as choose_system_loopback_microphone,
)


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
    """실제로 사용 중인 입력 장치명을 문자열로 반환한다."""

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

    return convert_float32_audio_to_pcm16_bytes(frames)


def select_system_loopback_microphone(soundcard_module: Any, device_name: str | None):
    """이름 또는 기본 loopback 마이크를 선택한다."""

    return choose_system_loopback_microphone(soundcard_module, device_name)


def list_microphone_devices() -> list[str]:
    """사용 가능한 마이크 장치 이름을 반환한다."""

    return list_available_microphone_devices()


def select_microphone_input_device(sounddevice_module: Any, device_name: str | None):
    """마이크 입력 장치를 선택한다."""

    return choose_microphone_input_device(sounddevice_module, device_name)


def list_system_audio_devices() -> list[str]:
    """사용 가능한 시스템 오디오 장치 이름을 반환한다."""

    return list_available_system_audio_devices()


def _has_data_discontinuity_warning(caught_warnings: list[warnings.WarningMessage]) -> bool:
    """data discontinuity 경고 포함 여부를 판별한다."""

    return has_data_discontinuity_warning(caught_warnings)


def _resolve_default_input_index(sounddevice_module: Any) -> int | None:
    """기본 입력 장치 index를 구한다."""

    return resolve_default_input_index(sounddevice_module)


def _resolve_sounddevice_name(sounddevice_module: Any, device_index: int) -> str:
    """index에서 sounddevice 장치 이름을 구한다."""

    return resolve_sounddevice_name(sounddevice_module, device_index)


def _is_likely_loopback_input_device_name(name: str) -> bool:
    """장치 이름이 loopback 계열인지 추정한다."""

    return is_likely_loopback_input_device_name(name)


def _import_numpy():
    """numpy를 지연 import한다."""

    from server.app.services.audio.io.live_audio_capture_helpers import import_numpy

    return import_numpy()


def _import_sounddevice():
    """sounddevice를 지연 import한다."""

    return import_sounddevice()


def _import_soundcard():
    """soundcard를 지연 import한다."""

    return import_soundcard()
