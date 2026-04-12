"""오디오 영역의 imports 서비스를 제공한다."""
from __future__ import annotations


def import_numpy():
    """numpy를 지연 import한다."""

    import numpy as np

    return np


def import_sounddevice():
    """sounddevice를 지연 import한다."""

    try:
        import sounddevice
    except ImportError as error:
        raise RuntimeError(
            "마이크 캡처를 사용하려면 sounddevice 패키지가 필요합니다. "
            "pip install sounddevice"
        ) from error
    return sounddevice


def import_soundcard():
    """soundcard를 지연 import한다."""

    try:
        import soundcard
    except ImportError as error:
        raise RuntimeError(
            "시스템 오디오 캡처를 사용하려면 soundcard 패키지가 필요합니다. "
            "pip install soundcard"
        ) from error
    return soundcard
