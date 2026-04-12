"""실시간 오디오 캡처 장치 선택 helper."""

from __future__ import annotations

import warnings
from typing import Any

from .imports import import_soundcard, import_sounddevice


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

    sounddevice = import_sounddevice()
    devices = []
    for device in sounddevice.query_devices():
        if device.get("max_input_channels", 0) > 0:
            devices.append(str(device.get("name")))
    return devices


def select_microphone_input_device(sounddevice_module: Any, device_name: str | None):
    """마이크 입력 장치를 선택한다."""

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

    default_input_index = resolve_default_input_index(sounddevice_module)
    if default_input_index is not None:
        default_name = resolve_sounddevice_name(sounddevice_module, default_input_index)
        if not is_likely_loopback_input_device_name(default_name):
            return default_input_index

    non_loopback_candidate = next(
        (index for index, name in input_candidates if not is_likely_loopback_input_device_name(name)),
        None,
    )
    if non_loopback_candidate is not None:
        return non_loopback_candidate

    return input_candidates[0][0]


def list_system_audio_devices() -> list[str]:
    """사용 가능한 시스템 오디오 장치 이름을 반환한다."""

    soundcard = import_soundcard()
    return [
        microphone.name
        for microphone in soundcard.all_microphones(include_loopback=True)
        if getattr(microphone, "isloopback", False)
    ]


def has_data_discontinuity_warning(caught_warnings: list[warnings.WarningMessage]) -> bool:
    """recording discontinuity 경고 포함 여부를 판별한다."""

    for warning in caught_warnings:
        if "data discontinuity in recording" in str(warning.message).casefold():
            return True
    return False


def resolve_default_input_index(sounddevice_module: Any) -> int | None:
    """sounddevice 기본 입력 장치 index를 구한다."""

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


def resolve_sounddevice_name(sounddevice_module: Any, device_index: int) -> str:
    """sounddevice index에서 장치 이름을 구한다."""

    try:
        device = sounddevice_module.query_devices(device_index)
    except Exception:
        return f"index={device_index}"
    return str(device.get("name", f"index={device_index}"))


def is_likely_loopback_input_device_name(name: str) -> bool:
    """장치 이름이 loopback 계열인지 추정한다."""

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
