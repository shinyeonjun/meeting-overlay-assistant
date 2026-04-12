"""실제 WAV 기반 STT acceptance 테스트.

기본 테스트 러닝에서는 건너뛴다.
RUN_STT_ACCEPTANCE=1 환경변수를 줄 때만 실행한다.
"""

from __future__ import annotations

import os
from pathlib import Path

import pytest

from tests.conftest import VIDEO_FIXTURES_ROOT
from server.app.services.audio.stt.benchmarking import (
    compute_character_error_rate,
    compute_word_error_rate,
)
from server.app.services.audio.segmentation.speech_segmenter import SpeechSegment
from server.app.services.audio.stt.speech_to_text_factory import create_speech_to_text_service
from server.app.services.audio.io.wav_chunk_reader import read_pcm_wave_file, split_pcm_bytes


pytestmark = pytest.mark.skipif(
    os.getenv("RUN_STT_ACCEPTANCE") != "1",
    reason="실제 모델 기반 acceptance 테스트는 수동 실행 전용입니다.",
)


def test_faster_whisper_실제_wav에서_기준_정확도_이하로_유지된다():
    wav_path = VIDEO_FIXTURES_ROOT / "test_16k_mono_15s.wav"
    reference_path = VIDEO_FIXTURES_ROOT / "test.txt"
    if not wav_path.exists() or not reference_path.exists():
        pytest.skip("acceptance 샘플 파일이 없습니다.")

    reference_text = reference_path.read_text(encoding="utf-8").strip()
    service = create_speech_to_text_service(
        backend_name="faster_whisper",
        model_id="deepdml/faster-whisper-large-v3-turbo-ct2",
        model_path=None,
        base_model_id=None,
        installation_path=None,
        encoder_model_path=None,
        decoder_model_path=None,
        encoder_rai_path=None,
        base_url=None,
        api_key=None,
        timeout_seconds=60,
        language="ko",
        device="auto",
        compute_type="default",
        cpu_threads=0,
        beam_size=1,
        sample_rate_hz=16000,
        sample_width_bytes=2,
        channels=1,
        silence_rms_threshold=0.003,
    )

    wave_audio = read_pcm_wave_file(
        wav_path,
        expected_sample_rate_hz=16000,
        expected_sample_width_bytes=2,
        expected_channels=1,
    )
    chunks = split_pcm_bytes(
        wave_audio.raw_bytes,
        sample_rate_hz=16000,
        sample_width_bytes=2,
        channels=1,
        chunk_duration_ms=250,
    )

    texts: list[str] = []
    start_ms = 0
    chunk_duration_ms = 250
    for chunk in chunks:
        result = service.transcribe(
            SpeechSegment(
                raw_bytes=chunk,
                start_ms=start_ms,
                end_ms=start_ms + chunk_duration_ms,
            )
        )
        start_ms += chunk_duration_ms
        if result.text.strip():
            texts.append(result.text.strip())

    transcript = " ".join(texts).strip()
    wer = compute_word_error_rate(reference_text, transcript).rate
    cer = compute_character_error_rate(reference_text, transcript).rate

    assert wer <= 0.35
    assert cer <= 0.25


