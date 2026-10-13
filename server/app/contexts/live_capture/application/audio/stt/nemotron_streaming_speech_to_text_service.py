"""NVIDIA Nemotron streaming ASR(transformers) 기반 회색 자막 서비스."""

from __future__ import annotations

from dataclasses import dataclass
import logging
from pathlib import Path
from threading import Lock
import weakref

from server.app.contexts.live_capture.application.audio.segmentation.speech_segmenter import SpeechSegment
from server.app.contexts.live_capture.application.audio.stt.common.preview_stability import normalize_text
from server.app.contexts.live_capture.application.audio.stt.nemotron.model_pool import (
    NemotronModelKey,
    NemotronModelPool,
    NemotronModelSlot,
    get_nemotron_model_pool,
)
from server.app.contexts.live_capture.application.audio.stt.nemotron.stream_session import (
    NemotronStreamSession,
    strip_language_tags,
)
from server.app.contexts.live_capture.application.audio.stt.sherpa.audio import (
    duration_ms_to_bytes,
    pcm16_to_float32_audio,
)

# preview/live_final 안정화 로직은 엔진과 무관해서 sherpa 구현을 그대로 쓴다.
from server.app.contexts.live_capture.application.audio.stt.sherpa.preview_results import (
    append_live_final_result,
    append_preview_result,
)
from server.app.contexts.live_capture.application.audio.stt.sherpa.state import (
    create_streaming_state,
    reset_streaming_state,
)
from server.app.contexts.live_capture.application.audio.stt.sherpa.streaming_logic import compute_stable_preview
from server.app.contexts.live_capture.application.audio.stt.transcription import (
    StreamingSpeechToTextService,
    TranscriptionResult,
    record_current_preview_stage,
)

logger = logging.getLogger(__name__)

_LANGUAGE_LOCALES = {"ko": "ko-KR", "en": "en-US", "ja": "ja-JP", "zh": "zh-CN"}
_WARMUP_SECONDS = 2.0


def resolve_nemotron_language(language: str | None) -> str:
    """'ko' 같은 짧은 코드를 Nemotron이 받는 'ko-KR' 형식으로 바꾼다."""

    if not language:
        return "ko-KR"
    return _LANGUAGE_LOCALES.get(language.strip().lower(), language.strip())


def resolve_nemotron_model_ref(*, model_id: str, model_path: str | None) -> str:
    """로컬 transformers 모델 폴더가 있으면 그 경로를, 없으면 Hugging Face 모델 ID를 쓴다.

    hybrid 빌더는 partial_model_path가 없으면 final 모델 경로를 넘기므로,
    config.json이 있는 폴더일 때만 로컬 경로로 인정한다.
    """

    if model_path:
        candidate = Path(model_path)
        if (candidate / "config.json").is_file():
            return str(candidate.resolve())
    return model_id


@dataclass(frozen=True)
class NemotronStreamingConfig:
    """Nemotron streaming 실행 설정."""

    model_ref: str
    language: str = "ko-KR"
    device: str = "cuda"
    dtype: str = "bfloat16"
    lookahead_tokens: int = 6
    sample_rate_hz: int = 16000
    sample_width_bytes: int = 2
    channels: int = 1
    partial_emit_interval_ms: int = 140
    partial_agreement_window: int = 2
    partial_agreement_min_count: int = 2
    partial_min_stable_chars: int = 3
    partial_min_growth_chars: int = 2
    partial_backtrack_tolerance_chars: int = 2
    partial_commit_min_chars_without_boundary: int = 3
    # 세션을 닫을 때 generate()가 끝나기를 기다리는 시간. 넘기면 그 모델은 다시 쓰지 않는다.
    join_timeout_seconds: float = 5.0

    @property
    def model_key(self) -> NemotronModelKey:
        return NemotronModelKey(
            model_ref=self.model_ref,
            device=self.device,
            dtype=self.dtype,
            lookahead_tokens=self.lookahead_tokens,
        )


class _SlotLease:
    """서비스가 빌린 모델 슬롯. 서비스가 사라지면 세션을 닫고 슬롯을 풀에 돌려준다."""

    def __init__(self, pool: NemotronModelPool) -> None:
        self.pool = pool
        self.slot: NemotronModelSlot | None = None
        self.session: NemotronStreamSession | None = None
        self.session_offset = 0  # 현재 세션이 시작된 스트림 샘플 위치

    def release(self) -> None:
        self.retire_session()
        if self.slot is not None:
            self.pool.release(self.slot)
            self.slot = None

    def retire_session(self) -> None:
        """세션을 닫는다. generate()가 제때 안 끝나면 그 모델은 풀에 돌려주지 않고 버린다."""

        session, self.session = self.session, None
        if session is None:
            return
        session.close()
        if not session.join() and self.slot is not None:
            logger.warning("끝나지 않은 Nemotron 모델 인스턴스를 풀에 돌려주지 않고 버립니다.")
            self.slot = None


class NemotronStreamingSpeechToTextService(StreamingSpeechToTextService):
    """회색 자막(preview/live_final)을 Nemotron streaming으로 만든다.

    preview_chunk()는 preview 작업 스레드에서, reset_stream()은 final 작업 스레드에서 불릴 수 있다.
    인식 세션은 확정이 나와도 끊지 않는다. 끊으면 그사이 들어온 다음 말의 앞부분을 잃고,
    새 세션은 첫 청크(약 0.5초)가 찰 때까지 글자를 못 내기 때문이다.
    """

    def __init__(self, config: NemotronStreamingConfig, *, pool: NemotronModelPool | None = None) -> None:
        self._config = config
        self._lease = _SlotLease(pool or get_nemotron_model_pool(config.model_key))
        self._finalizer = weakref.finalize(self, self._lease.release)
        self._lock = Lock()
        self._pushed_samples = 0  # 스트림 처음부터 받은 샘플 수
        self._state = create_streaming_state(history_size=max(config.partial_agreement_window, 1))
        self._emit_interval_bytes = duration_ms_to_bytes(
            duration_ms=config.partial_emit_interval_ms,
            sample_rate_hz=config.sample_rate_hz,
            sample_width_bytes=config.sample_width_bytes,
            channels=config.channels,
        )

    @property
    def backend_name(self) -> str:
        return "nemotron_streaming"

    def preload(self) -> None:
        """모델을 올리고 짧은 무음으로 한 번 돌려 첫 세션의 CUDA 초기화 지연을 없앤다."""

        import numpy as np

        pool = self._lease.pool
        slot = pool.acquire()
        session = self._new_session(slot)
        session.push(np.zeros(int(self._config.sample_rate_hz * _WARMUP_SECONDS), dtype=np.float32))
        session.close()
        if session.join():
            pool.release(slot)
        if session.error is not None:
            raise RuntimeError("Nemotron 예열 실패") from session.error

    def preview_chunk(self, chunk: bytes) -> list[TranscriptionResult]:
        if not chunk:
            return []

        with self._lock:
            session = self._ensure_session()
            samples = self._to_float32(chunk)
            session.push(samples)
            self._pushed_samples += int(samples.size)
            self._state.bytes_since_emit += len(chunk)
            if self._state.bytes_since_emit < self._emit_interval_bytes:
                return []
            self._state.bytes_since_emit = 0

            current_text = session.text
            normalized_text = normalize_text(current_text)
            if not normalized_text:
                return []
            # 모니터 API 필드 이름(sherpa_non_empty)을 유지하려고 같은 stage 이름을 쓴다.
            record_current_preview_stage("sherpa_non_empty")

            results: list[TranscriptionResult] = []
            append_preview_result(
                state=self._state,
                current_text=current_text,
                normalized_text=normalized_text,
                results=results,
            )
            self._state.preview_history.append(normalized_text)
            stable_preview = self._compute_stable_preview(current_text)
            append_live_final_result(state=self._state, stable_preview=stable_preview, results=results)
            return results

    def reset_stream(self) -> None:
        """확정이 나온 뒤 부른다. 인식은 이어 가고 회색 자막 텍스트만 이 시점부터 다시 모은다."""

        with self._lock:
            if self._lease.session is not None:
                self._lease.session.mark()
            reset_streaming_state(self._state)

    def reset_stream_at(self, stream_end_sample: int) -> None:
        """확정 구간이 끝난 오디오 위치(스트림 샘플)를 경계로 회색 자막을 새로 모은다.

        확정이 나온 시각에도 모델은 앞 구간 끝부분을 아직 처리 중일 수 있어서,
        시각이 아니라 오디오 위치로 끊어야 앞 문장 끝이 다음 회색 자막에 붙지 않는다.
        """

        with self._lock:
            if self._lease.session is not None:
                self._lease.session.mark(stream_end_sample - self._lease.session_offset)
            reset_streaming_state(self._state)

    def transcribe(self, segment: SpeechSegment) -> TranscriptionResult:
        """구간 하나를 같은 streaming 경로로 끝까지 돌려 텍스트를 낸다 (hybrid에서는 쓰지 않는다)."""

        with self._lock:
            self._retire_current_session()
            session = self._new_session(self._ensure_slot())
            session.push(self._to_float32(segment.raw_bytes))
            session.close()
            session.join()
            return TranscriptionResult(text=strip_language_tags(session.text), confidence=0.8, kind="final")

    def close(self) -> None:
        """빌린 모델 슬롯을 즉시 돌려준다."""

        with self._lock:
            self._finalizer()

    def _ensure_slot(self) -> NemotronModelSlot:
        if self._lease.slot is None:
            self._lease.slot = self._lease.pool.acquire()
        return self._lease.slot

    def _ensure_session(self) -> NemotronStreamSession:
        session = self._lease.session
        if session is not None and session.usable:
            return session
        slot = self._ensure_slot()
        if session is not None:
            # generate()가 오류로 끝난 세션. 같은 모델로 generate()가 겹치지 않게 정리한 뒤 새로 연다.
            logger.warning("Nemotron 인식 세션이 끝나 있어 새로 엽니다: error=%r", session.error)
            self._lease.retire_session()
            slot = self._ensure_slot()
        self._lease.session = self._new_session(slot)
        self._lease.session_offset = self._pushed_samples
        return self._lease.session

    def _retire_current_session(self) -> None:
        self._lease.retire_session()

    def _new_session(self, slot: NemotronModelSlot) -> NemotronStreamSession:
        return NemotronStreamSession(
            model=slot.model,
            processor=slot.processor,
            language=self._config.language,
            sample_rate_hz=self._config.sample_rate_hz,
            join_timeout_seconds=self._config.join_timeout_seconds,
        )

    def _compute_stable_preview(self, latest_text: str) -> str:
        stable_preview = compute_stable_preview(
            preview_history=list(self._state.preview_history),
            latest_text=latest_text,
            last_stable_preview=self._state.last_stable_preview,
            last_emitted_live_final=self._state.last_emitted_live_final,
            agreement_min_count=self._config.partial_agreement_min_count,
            min_stable_chars=self._config.partial_min_stable_chars,
            min_growth_chars=self._config.partial_min_growth_chars,
            backtrack_tolerance_chars=self._config.partial_backtrack_tolerance_chars,
            commit_min_chars_without_boundary=self._config.partial_commit_min_chars_without_boundary,
        )
        if stable_preview:
            self._state.last_stable_preview = stable_preview
        return stable_preview

    def _to_float32(self, raw_bytes: bytes):
        import numpy as np

        return pcm16_to_float32_audio(
            raw_bytes=raw_bytes,
            sample_width_bytes=self._config.sample_width_bytes,
            channels=self._config.channels,
            np_module=np,
        )
