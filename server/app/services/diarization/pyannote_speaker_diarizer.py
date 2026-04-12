"""pyannote 기반 화자 분리 구현체를 제공한다.

Pyannote는 정확도는 좋지만 모델 다운로드, Hugging Face 토큰, torch 장치
구성 같은 준비 조건이 많다. 이 모듈은 그런 운영 제약을 런타임 오류 메시지에
명확히 드러내서 디버깅 비용을 낮추는 것을 같이 목표로 한다.
"""
from __future__ import annotations

from array import array
from dataclasses import dataclass

from server.app.services.audio.preprocessing.audio_preprocessing import AudioBuffer
from server.app.services.diarization.speaker_diarizer import SpeakerSegment


@dataclass(frozen=True)
class PyannoteDiarizerConfig:
    """pyannote 화자 분리 설정.

    model_id와 auth_token은 Hugging Face 모델 접근에 필요하고, device는
    CPU 기본 경로에서 검증한 뒤에만 GPU/NPU로 올리는 것을 권장한다.
    """

    model_id: str
    auth_token: str | None = None
    device: str = "cpu"


class PyannoteSpeakerDiarizer:
    """pyannote.audio 파이프라인을 사용해 화자 구간을 추정한다."""

    def __init__(self, config: PyannoteDiarizerConfig) -> None:
        self._config = config
        self._pipeline = None

    def diarize(self, audio: AudioBuffer) -> list[SpeakerSegment]:
        """오디오를 pyannote 입력 형식으로 변환한 뒤 diarization을 수행한다."""

        if not audio.raw_bytes:
            return []
        if not self._config.auth_token:
            raise RuntimeError(
                "pyannote 화자 분리기는 Hugging Face 토큰이 필요합니다. "
                "`.env`의 `SPEAKER_DIARIZER_AUTH_TOKEN` 또는 `HF_TOKEN`을 설정하세요."
            )

        pipeline = self._get_pipeline()
        waveform_input = self._build_waveform_input(audio)
        diarization_result = pipeline(waveform_input)
        return self._extract_segments(diarization_result)

    def _get_pipeline(self):
        """파이프라인을 지연 초기화해서 첫 요청 이후에는 재사용한다."""

        if self._pipeline is None:
            self._pipeline = self._build_pipeline()
        return self._pipeline

    def _build_pipeline(self):
        """pyannote 파이프라인을 로드하고 필요한 장치로 이동시킨다."""

        try:
            pyannote_audio = __import__("pyannote.audio", fromlist=["Pipeline"])
        except ImportError as exc:
            raise RuntimeError(
                "pyannote.audio 화자 분리기는 아직 설치되지 않았습니다. "
                "추후 Hugging Face 토큰과 함께 설치한 뒤 다시 시도하세요."
            ) from exc

        pipeline_factory = getattr(pyannote_audio, "Pipeline")
        try:
            pipeline = pipeline_factory.from_pretrained(
                self._config.model_id,
                token=self._config.auth_token,
            )
        except TypeError:
            pipeline = pipeline_factory.from_pretrained(
                self._config.model_id,
                use_auth_token=self._config.auth_token,
            )

        self._move_pipeline_to_device(pipeline)
        return pipeline

    def _move_pipeline_to_device(self, pipeline) -> None:  # noqa: ANN001
        """CPU가 아닌 경우에만 torch 장치 이동을 시도한다."""

        if self._config.device == "cpu":
            return

        try:
            torch_module = __import__("torch")
        except ImportError as exc:
            raise RuntimeError(
                "pyannote GPU/NPU 장치를 사용하려면 torch가 필요합니다."
            ) from exc

        try:
            pipeline.to(torch_module.device(self._config.device))
        except RuntimeError as exc:
            raise RuntimeError(
                "pyannote를 현재 장치로 이동하지 못했습니다. "
                "지금 환경에서는 `SPEAKER_DIARIZER_DEVICE=cpu`로 먼저 검증하는 편이 안전합니다."
            ) from exc

    @staticmethod
    def _build_waveform_input(audio: AudioBuffer) -> dict[str, object]:
        """AudioBuffer를 pyannote가 기대하는 waveform dict로 변환한다.

        현재는 16-bit PCM만 지원한다. 다른 sample width는 downstream torch
        텐서 스케일링 가정을 깨므로 초기에 명시적으로 막는다.
        """

        if audio.sample_width_bytes != 2:
            raise ValueError("pyannote 화자 분리기는 현재 16-bit PCM 입력만 지원합니다.")

        try:
            torch_module = __import__("torch")
        except ImportError as exc:
            raise RuntimeError(
                "pyannote waveform 입력을 만들려면 torch가 필요합니다."
            ) from exc

        samples = array("h")
        samples.frombytes(audio.raw_bytes)
        waveform = torch_module.tensor(samples, dtype=torch_module.float32) / 32768.0

        if audio.channels > 1:
            waveform = waveform.reshape(-1, audio.channels).transpose(0, 1)
        else:
            waveform = waveform.unsqueeze(0)

        return {
            "waveform": waveform,
            "sample_rate": audio.sample_rate_hz,
        }

    @staticmethod
    def _extract_segments(diarization_result) -> list[SpeakerSegment]:  # noqa: ANN001
        """pyannote 결과를 프로젝트 공통 SpeakerSegment 목록으로 변환한다."""

        segments: list[SpeakerSegment] = []
        for turn, _, speaker_label in diarization_result.itertracks(yield_label=True):
            segments.append(
                SpeakerSegment(
                    speaker_label=str(speaker_label),
                    start_ms=int(float(turn.start) * 1000),
                    end_ms=int(float(turn.end) * 1000),
                )
            )
        return segments
