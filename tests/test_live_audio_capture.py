"""실시간 오디오 캡처 보조 로직 테스트."""

from __future__ import annotations

import numpy as np
import pytest

from backend.app.services.audio.io.live_audio_capture import (
    LiveAudioCaptureConfig,
    _has_data_discontinuity_warning,
    _is_likely_loopback_input_device_name,
    create_live_audio_capture,
    float32_audio_to_pcm16_bytes,
    resolve_live_capture_device_label,
    select_microphone_input_device,
    select_system_loopback_microphone,
)


class _Speaker:
    def __init__(self, name: str, speaker_id: str = "speaker-id") -> None:
        self.name = name
        self.id = speaker_id


class _Microphone:
    def __init__(self, name: str, isloopback: bool) -> None:
        self.name = name
        self.isloopback = isloopback


class _SoundcardModule:
    def __init__(self) -> None:
        self._speakers = [_Speaker("Speaker A", "A"), _Speaker("Speaker B", "B")]
        self._microphones = [
            _Microphone("Speaker A", True),
            _Microphone("Microphone A", False),
            _Microphone("Speaker B", True),
        ]

    def all_speakers(self):
        return self._speakers

    def default_speaker(self):
        return self._speakers[0]

    def all_microphones(self, include_loopback: bool = False):
        if include_loopback:
            return self._microphones
        return [microphone for microphone in self._microphones if not microphone.isloopback]

    def get_microphone(self, speaker_id: str, include_loopback: bool = False):
        assert include_loopback is True
        for speaker in self._speakers:
            if speaker.id == speaker_id:
                return _Microphone(speaker.name, True)
        raise ValueError("speaker not found")


class _SounddeviceDefault:
    def __init__(self, device):
        self.device = device


class _SounddeviceModule:
    def __init__(self, devices: list[dict], default_device=(0, 0)) -> None:
        self._devices = devices
        self.default = _SounddeviceDefault(default_device)

    def query_devices(self, device_index: int | None = None):
        if device_index is None:
            return self._devices
        return self._devices[device_index]


class TestLiveAudioCapture:
    """실시간 오디오 캡처 보조 로직을 검증한다."""

    def test_float32_프레임을_pcm16_bytes로_변환한다(self):
        frames = np.asarray([0.0, 0.5, -0.5], dtype=np.float32)

        pcm_bytes = float32_audio_to_pcm16_bytes(frames)

        assert pcm_bytes == np.asarray([0, 16383, -16383], dtype=np.int16).tobytes()

    def test_frames_per_chunk를_계산한다(self):
        config = LiveAudioCaptureConfig(source="mic", sample_rate_hz=16000, chunk_duration_ms=250)

        assert config.frames_per_chunk == 4000

    def test_시스템_오디오_장치_이름으로_loopback_마이크를_선택한다(self):
        speaker = select_system_loopback_microphone(_SoundcardModule(), "Speaker B")

        assert speaker.name == "Speaker B"

    def test_없는_장치를_선택하면_예외를_발생시킨다(self):
        with pytest.raises(ValueError):
            select_system_loopback_microphone(_SoundcardModule(), "Missing Speaker")

    def test_source에_맞는_capture를_생성한다(self):
        mic_capture = create_live_audio_capture(LiveAudioCaptureConfig(source="mic"))
        system_capture = create_live_audio_capture(LiveAudioCaptureConfig(source="system_audio"))

        assert mic_capture.__class__.__name__ == "MicrophoneAudioCapture"
        assert system_capture.__class__.__name__ == "SystemAudioLoopbackCapture"

    def test_data_discontinuity_warning을_감지한다(self):
        warning_message = UserWarning("data discontinuity in recording")
        warning_item = type("WarningItem", (), {"message": warning_message})()

        assert _has_data_discontinuity_warning([warning_item]) is True
        assert _has_data_discontinuity_warning([]) is False

    def test_mic_명시_장치명이_있으면_그_장치를_선택한다(self):
        sounddevice = _SounddeviceModule(
            devices=[
                {"name": "Stereo Mix", "max_input_channels": 2},
                {"name": "USB Microphone", "max_input_channels": 1},
            ],
            default_device=(0, 0),
        )

        selected = select_microphone_input_device(sounddevice, "USB Microphone")

        assert selected == 1

    def test_default가_loopback이면_non_loopback_장치를_선택한다(self):
        sounddevice = _SounddeviceModule(
            devices=[
                {"name": "Stereo Mix", "max_input_channels": 2},
                {"name": "Realtek Microphone", "max_input_channels": 1},
            ],
            default_device=(0, 0),
        )

        selected = select_microphone_input_device(sounddevice, None)

        assert selected == 1

    def test_default가_non_loopback이면_default를_유지한다(self):
        sounddevice = _SounddeviceModule(
            devices=[
                {"name": "Realtek Microphone", "max_input_channels": 1},
                {"name": "Stereo Mix", "max_input_channels": 2},
            ],
            default_device=(0, 0),
        )

        selected = select_microphone_input_device(sounddevice, None)

        assert selected == 0

    def test_loopback_키워드를_감지한다(self):
        assert _is_likely_loopback_input_device_name("Stereo Mix (Realtek)") is True
        assert _is_likely_loopback_input_device_name("VB-Audio Cable Output") is True
        assert _is_likely_loopback_input_device_name("USB Microphone") is False

    def test_mic_입력_장치명을_해석한다(self, monkeypatch):
        import backend.app.services.audio.io.live_audio_capture as module

        fake_sounddevice = _SounddeviceModule(
            devices=[
                {"name": "Stereo Mix", "max_input_channels": 2},
                {"name": "USB Microphone", "max_input_channels": 1},
            ],
            default_device=(1, 0),
        )
        monkeypatch.setattr(module, "_import_sounddevice", lambda: fake_sounddevice)

        label = resolve_live_capture_device_label(LiveAudioCaptureConfig(source="mic"))

        assert label == "USB Microphone"

