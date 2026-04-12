"""KsponSpeech baseline 평가 스크립트."""

from __future__ import annotations

import argparse
import json
import re
import statistics
import sys
import time
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[3]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from server.app.core.config import settings  # noqa: E402
from server.app.domain.models.utterance import Utterance  # noqa: E402
from server.app.services.analysis.llm.factories.completion_client_factory import (  # noqa: E402
    create_llm_completion_client,
)
from server.app.services.audio.segmentation.models import SpeechSegment  # noqa: E402
from server.app.services.audio.stt.benchmarking import (  # noqa: E402
    compute_character_error_rate,
    compute_word_error_rate,
)
from server.app.services.reports.refinement import (  # noqa: E402
    NoteTranscriptCorrectionConfig,
    NoteTranscriptCorrector,
)
from server.app.services.audio.stt.speech_to_text_factory import create_speech_to_text_service  # noqa: E402


DEFAULT_MANIFEST_PATH = Path(
    r"D:\stt_data\fine_tuning\eval_sets\public_baseline\ksponspeech_eval_quick200.jsonl"
)
DEFAULT_OUTPUT_ROOT = Path(r"D:\stt_data\fine_tuning\runs")

DIGIT_TOKEN_PATTERN = re.compile(r"\d[\d,.:/-]*")
LATIN_TOKEN_PATTERN = re.compile(r"[A-Za-z][A-Za-z0-9._/-]*")


@dataclass(frozen=True)
class BaselineSample:
    """평가에 사용할 KsponSpeech 샘플."""

    dataset: str
    split: str
    audio_path: Path
    audio_format: str
    relative_path: str
    source_relative_path: str
    reference_raw: str
    reference_display: str

    @property
    def sample_name(self) -> str:
        return Path(self.relative_path).stem


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="KsponSpeech baseline 평가를 실행합니다.")
    parser.add_argument(
        "--manifest",
        default=str(DEFAULT_MANIFEST_PATH),
        help="평가할 JSONL manifest 경로",
    )
    parser.add_argument(
        "--backend",
        default="faster_whisper",
        help="평가할 STT backend 이름",
    )
    parser.add_argument(
        "--backend-model",
        help="backend에 사용할 모델 ID override",
    )
    parser.add_argument(
        "--model-path",
        help="모델 경로 override",
    )
    parser.add_argument(
        "--beam-size",
        type=int,
        help="beam size override",
    )
    parser.add_argument(
        "--device",
        help="device override",
    )
    parser.add_argument(
        "--compute-type",
        help="compute type override",
    )
    parser.add_argument(
        "--run-label",
        help="결과 파일명에 붙일 라벨",
    )
    parser.add_argument(
        "--limit",
        type=int,
        help="앞에서부터 평가할 샘플 수 제한",
    )
    parser.add_argument(
        "--offset",
        type=int,
        default=0,
        help="건너뛸 샘플 수",
    )
    parser.add_argument(
        "--sample-rate",
        type=int,
        default=16000,
        help="PCM 샘플레이트",
    )
    parser.add_argument(
        "--sample-width-bytes",
        type=int,
        default=2,
        help="PCM 샘플 폭(byte)",
    )
    parser.add_argument(
        "--channels",
        type=int,
        default=1,
        help="PCM 채널 수",
    )
    parser.add_argument(
        "--preload",
        action="store_true",
        help="평가 전에 모델 preload를 수행",
    )
    parser.add_argument(
        "--output-json",
        help="요약 결과 JSON 저장 경로",
    )
    parser.add_argument(
        "--output-jsonl",
        help="샘플별 결과 JSONL 저장 경로",
    )
    parser.add_argument(
        "--apply-note-correction",
        action="store_true",
        help="note transcript 후보정을 적용한 비교 지표도 함께 계산",
    )
    parser.add_argument(
        "--correction-backend",
        help="후보정 backend override",
    )
    parser.add_argument(
        "--correction-model",
        help="후보정 model override",
    )
    parser.add_argument(
        "--correction-base-url",
        help="후보정 base URL override",
    )
    parser.add_argument(
        "--correction-timeout-seconds",
        type=float,
        help="후보정 timeout override",
    )
    parser.add_argument(
        "--correction-max-window",
        type=int,
        help="후보정 문맥 window override",
    )
    return parser


def load_samples(manifest_path: Path, *, offset: int, limit: int | None) -> list[BaselineSample]:
    samples: list[BaselineSample] = []
    with manifest_path.open("r", encoding="utf-8-sig") as handle:
        for index, line in enumerate(handle):
            if index < offset:
                continue
            payload = json.loads(line)
            samples.append(
                BaselineSample(
                    dataset=payload["dataset"],
                    split=payload["split"],
                    audio_path=Path(payload["audio_path"]),
                    audio_format=payload["audio_format"],
                    relative_path=payload["relative_path"],
                    source_relative_path=payload["source_relative_path"],
                    reference_raw=payload["reference_raw"],
                    reference_display=payload["reference_display"],
                )
            )
            if limit is not None and len(samples) >= limit:
                break
    return samples


def read_pcm_audio(
    path: Path,
    *,
    sample_rate: int,
    sample_width_bytes: int,
    channels: int,
) -> tuple[bytes, float]:
    raw_bytes = path.read_bytes()
    bytes_per_second = sample_rate * sample_width_bytes * channels
    if bytes_per_second <= 0:
        raise ValueError("PCM 메타데이터가 올바르지 않습니다.")
    duration_seconds = len(raw_bytes) / bytes_per_second
    return raw_bytes, duration_seconds


def build_stt_service(
    backend_name: str,
    backend_model: str | None,
    *,
    model_path: str | None,
    beam_size: int | None,
    device: str | None,
    compute_type: str | None,
):
    model_id = backend_model or settings.stt_model_id
    return create_speech_to_text_service(
        backend_name=backend_name,
        model_id=model_id,
        model_path=model_path or settings.stt_model_path,
        base_model_id=settings.stt_base_model_id,
        installation_path=settings.ryzen_ai_installation_path,
        encoder_model_path=settings.stt_encoder_model_path,
        decoder_model_path=settings.stt_decoder_model_path,
        encoder_rai_path=settings.stt_encoder_rai_path,
        base_url=settings.stt_base_url,
        api_key=settings.stt_api_key,
        timeout_seconds=settings.stt_timeout_seconds,
        language=settings.stt_language,
        initial_prompt=settings.stt_initial_prompt,
        device=device or settings.stt_device,
        compute_type=compute_type or settings.stt_compute_type,
        cpu_threads=settings.stt_cpu_threads,
        beam_size=beam_size if beam_size is not None else settings.stt_beam_size,
        sample_rate_hz=settings.stt_sample_rate_hz,
        sample_width_bytes=settings.stt_sample_width_bytes,
        channels=settings.stt_channels,
        silence_rms_threshold=settings.stt_silence_rms_threshold,
        partial_buffer_ms=settings.partial_buffer_ms,
        partial_emit_interval_ms=settings.partial_emit_interval_ms,
        partial_min_rms_threshold=settings.partial_min_rms_threshold,
        partial_agreement_window=settings.partial_agreement_window,
        partial_agreement_min_count=settings.partial_agreement_min_count,
        partial_min_stable_chars=settings.partial_min_stable_chars,
        partial_min_growth_chars=settings.partial_min_growth_chars,
        partial_backtrack_tolerance_chars=settings.partial_backtrack_tolerance_chars,
        partial_commit_min_chars_without_boundary=settings.partial_commit_min_chars_without_boundary,
    )


def build_note_transcript_corrector(
    *,
    backend_name: str | None,
    model: str | None,
    base_url: str | None,
    timeout_seconds: float | None,
    max_window: int | None,
) -> NoteTranscriptCorrector:
    completion_client = create_llm_completion_client(
        backend_name=backend_name or settings.note_transcript_correction_backend,
        model=model or settings.note_transcript_correction_model,
        base_url=base_url or settings.note_transcript_correction_base_url or "http://127.0.0.1:11434/v1",
        api_key=settings.note_transcript_correction_api_key,
        timeout_seconds=timeout_seconds or settings.note_transcript_correction_timeout_seconds,
    )
    return NoteTranscriptCorrector(
        completion_client,
        config=NoteTranscriptCorrectionConfig(
            model=model or settings.note_transcript_correction_model,
            max_window=max_window or settings.note_transcript_correction_max_window,
        ),
    )


def apply_note_correction(
    *,
    corrector: NoteTranscriptCorrector,
    sample: BaselineSample,
    hypothesis_text: str,
    confidence: float,
    duration_seconds: float,
) -> dict[str, Any]:
    utterance = Utterance.create(
        session_id=f"eval-{sample.sample_name}",
        seq_num=1,
        start_ms=0,
        end_ms=max(int(duration_seconds * 1000), 1),
        text=hypothesis_text,
        confidence=confidence,
        speaker_label="SPEAKER_00",
        transcript_source="post_processed",
        processing_job_id="eval-job",
    )
    document = corrector.correct(
        session_id=f"eval-{sample.sample_name}",
        source_version=1,
        utterances=[utterance],
    )
    item = document.items[0]
    corrected_text = item.corrected_text.strip() or hypothesis_text
    corrected_wer = compute_word_error_rate(sample.reference_display, corrected_text)
    corrected_cer = compute_character_error_rate(sample.reference_display, corrected_text)
    corrected_digit_metrics = compute_token_preservation(
        sample.reference_display,
        corrected_text,
        DIGIT_TOKEN_PATTERN,
    )
    corrected_latin_metrics = compute_token_preservation(
        sample.reference_display,
        corrected_text,
        LATIN_TOKEN_PATTERN,
    )
    return {
        "corrected_text": corrected_text,
        "correction_changed": item.changed,
        "correction_risk_flags": item.risk_flags,
        "corrected_wer": corrected_wer.__dict__,
        "corrected_cer": corrected_cer.__dict__,
        "corrected_digit_metrics": corrected_digit_metrics,
        "corrected_latin_metrics": corrected_latin_metrics,
        "corrected_exact_match": normalize_text(sample.reference_display) == normalize_text(corrected_text),
    }


def evaluate_sample(
    service: Any,
    sample: BaselineSample,
    *,
    corrector: NoteTranscriptCorrector | None,
    sample_rate: int,
    sample_width_bytes: int,
    channels: int,
) -> dict[str, Any]:
    if sample.audio_format.lower() != "pcm":
        raise ValueError(f"아직 지원하지 않는 audio_format입니다: {sample.audio_format}")

    raw_bytes, duration_seconds = read_pcm_audio(
        sample.audio_path,
        sample_rate=sample_rate,
        sample_width_bytes=sample_width_bytes,
        channels=channels,
    )
    segment = SpeechSegment(
        start_ms=0,
        end_ms=max(int(duration_seconds * 1000), 1),
        raw_bytes=raw_bytes,
    )

    started_at = time.perf_counter()
    transcription = service.transcribe(segment)
    elapsed_seconds = time.perf_counter() - started_at

    hypothesis_text = transcription.text.strip()
    wer = compute_word_error_rate(sample.reference_display, hypothesis_text)
    cer = compute_character_error_rate(sample.reference_display, hypothesis_text)
    digit_metrics = compute_token_preservation(
        sample.reference_display,
        hypothesis_text,
        DIGIT_TOKEN_PATTERN,
    )
    latin_metrics = compute_token_preservation(
        sample.reference_display,
        hypothesis_text,
        LATIN_TOKEN_PATTERN,
    )

    result = {
        "sample_name": sample.sample_name,
        "dataset": sample.dataset,
        "split": sample.split,
        "audio_path": str(sample.audio_path),
        "audio_format": sample.audio_format,
        "duration_seconds": round(duration_seconds, 4),
        "elapsed_seconds": round(elapsed_seconds, 4),
        "rtf": round(elapsed_seconds / duration_seconds, 4) if duration_seconds > 0 else None,
        "reference_text": sample.reference_display,
        "hypothesis_text": hypothesis_text,
        "confidence": round(transcription.confidence, 4),
        "no_speech_prob": (
            round(transcription.no_speech_prob, 4)
            if transcription.no_speech_prob is not None
            else None
        ),
        "wer": wer.__dict__,
        "cer": cer.__dict__,
        "digit_metrics": digit_metrics,
        "latin_metrics": latin_metrics,
        "exact_match": normalize_text(sample.reference_display) == normalize_text(hypothesis_text),
    }
    if corrector is not None:
        result.update(
            apply_note_correction(
                corrector=corrector,
                sample=sample,
                hypothesis_text=hypothesis_text,
                confidence=transcription.confidence,
                duration_seconds=duration_seconds,
            )
        )
    return result


def compute_token_preservation(
    reference_text: str,
    hypothesis_text: str,
    pattern: re.Pattern[str],
) -> dict[str, Any]:
    reference_tokens = pattern.findall(reference_text)
    hypothesis_tokens = pattern.findall(hypothesis_text)
    reference_counter = Counter(reference_tokens)
    hypothesis_counter = Counter(hypothesis_tokens)
    matched_count = sum((reference_counter & hypothesis_counter).values())
    reference_count = sum(reference_counter.values())
    hypothesis_count = sum(hypothesis_counter.values())
    recall = round(matched_count / reference_count, 4) if reference_count else None
    precision = round(matched_count / hypothesis_count, 4) if hypothesis_count else None
    return {
        "reference_tokens": reference_tokens,
        "hypothesis_tokens": hypothesis_tokens,
        "reference_count": reference_count,
        "hypothesis_count": hypothesis_count,
        "matched_count": matched_count,
        "recall": recall,
        "precision": precision,
    }


def normalize_text(text: str) -> str:
    return " ".join(text.split()).strip()


def aggregate_results(sample_results: list[dict[str, Any]]) -> dict[str, Any]:
    wer_rates = [item["wer"]["rate"] for item in sample_results]
    cer_rates = [item["cer"]["rate"] for item in sample_results]
    rtfs = [item["rtf"] for item in sample_results if item["rtf"] is not None]
    exact_match_count = sum(1 for item in sample_results if item["exact_match"])

    digit_samples = [item for item in sample_results if item["digit_metrics"]["reference_count"] > 0]
    latin_samples = [item for item in sample_results if item["latin_metrics"]["reference_count"] > 0]

    aggregate = {
        "sample_count": len(sample_results),
        "avg_wer": round(statistics.mean(wer_rates), 4) if wer_rates else None,
        "median_wer": round(statistics.median(wer_rates), 4) if wer_rates else None,
        "avg_cer": round(statistics.mean(cer_rates), 4) if cer_rates else None,
        "median_cer": round(statistics.median(cer_rates), 4) if cer_rates else None,
        "avg_rtf": round(statistics.mean(rtfs), 4) if rtfs else None,
        "exact_match_rate": round(exact_match_count / len(sample_results), 4) if sample_results else None,
        "digit_token_recall": summarize_token_metric(digit_samples, "digit_metrics"),
        "latin_token_recall": summarize_token_metric(latin_samples, "latin_metrics"),
    }
    corrected_samples = [item for item in sample_results if item.get("corrected_wer")]
    if corrected_samples:
        corrected_wer_rates = [item["corrected_wer"]["rate"] for item in corrected_samples]
        corrected_cer_rates = [item["corrected_cer"]["rate"] for item in corrected_samples]
        corrected_exact_match_count = sum(
            1 for item in corrected_samples if item.get("corrected_exact_match")
        )
        corrected_digit_samples = [
            item
            for item in corrected_samples
            if item["corrected_digit_metrics"]["reference_count"] > 0
        ]
        corrected_latin_samples = [
            item
            for item in corrected_samples
            if item["corrected_latin_metrics"]["reference_count"] > 0
        ]
        aggregate["correction"] = {
            "sample_count": len(corrected_samples),
            "avg_wer": round(statistics.mean(corrected_wer_rates), 4) if corrected_wer_rates else None,
            "median_wer": round(statistics.median(corrected_wer_rates), 4)
            if corrected_wer_rates
            else None,
            "avg_cer": round(statistics.mean(corrected_cer_rates), 4) if corrected_cer_rates else None,
            "median_cer": round(statistics.median(corrected_cer_rates), 4)
            if corrected_cer_rates
            else None,
            "exact_match_rate": round(corrected_exact_match_count / len(corrected_samples), 4)
            if corrected_samples
            else None,
            "digit_token_recall": summarize_token_metric(
                corrected_digit_samples, "corrected_digit_metrics"
            ),
            "latin_token_recall": summarize_token_metric(
                corrected_latin_samples, "corrected_latin_metrics"
            ),
            "changed_rate": round(
                sum(1 for item in corrected_samples if item.get("correction_changed"))
                / len(corrected_samples),
                4,
            )
            if corrected_samples
            else None,
            "delta_avg_wer": round(
                statistics.mean(corrected_wer_rates) - statistics.mean(wer_rates),
                4,
            )
            if wer_rates and corrected_wer_rates
            else None,
            "delta_avg_cer": round(
                statistics.mean(corrected_cer_rates) - statistics.mean(cer_rates),
                4,
            )
            if cer_rates and corrected_cer_rates
            else None,
        }
    return aggregate
    

def summarize_token_metric(
    sample_results: list[dict[str, Any]],
    metric_key: str,
) -> dict[str, Any]:
    if not sample_results:
        return {
            "sample_count": 0,
            "avg_recall": None,
            "avg_precision": None,
        }

    recalls = [
        item[metric_key]["recall"]
        for item in sample_results
        if item[metric_key]["recall"] is not None
    ]
    precisions = [
        item[metric_key]["precision"]
        for item in sample_results
        if item[metric_key]["precision"] is not None
    ]
    return {
        "sample_count": len(sample_results),
        "avg_recall": round(statistics.mean(recalls), 4) if recalls else None,
        "avg_precision": round(statistics.mean(precisions), 4) if precisions else None,
    }


def resolve_output_path(
    output_json: str | None,
    *,
    backend_name: str,
    sample_count: int,
    run_label: str | None,
) -> Path:
    if output_json:
        return Path(output_json).resolve()
    timestamp = time.strftime("%Y%m%d-%H%M%S")
    label_suffix = f"-{sanitize_label(run_label)}" if run_label else ""
    return (
        DEFAULT_OUTPUT_ROOT
        / f"ksponspeech-baseline-{backend_name}-{sample_count}{label_suffix}-{timestamp}.json"
    ).resolve()


def resolve_output_jsonl_path(output_jsonl: str | None, *, output_json_path: Path) -> Path:
    if output_jsonl:
        return Path(output_jsonl).resolve()
    return output_json_path.with_suffix(".samples.jsonl")


def sanitize_label(value: str) -> str:
    return re.sub(r"[^A-Za-z0-9._-]+", "-", value).strip("-") or "run"


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()

    manifest_path = Path(args.manifest).resolve()
    samples = load_samples(
        manifest_path,
        offset=max(args.offset, 0),
        limit=args.limit if args.limit and args.limit > 0 else None,
    )
    if not samples:
        raise SystemExit("평가할 샘플이 없습니다.")

    service = build_stt_service(
        args.backend,
        args.backend_model,
        model_path=args.model_path,
        beam_size=args.beam_size,
        device=args.device,
        compute_type=args.compute_type,
    )
    corrector = None
    if args.apply_note_correction:
        corrector = build_note_transcript_corrector(
            backend_name=args.correction_backend,
            model=args.correction_model,
            base_url=args.correction_base_url,
            timeout_seconds=args.correction_timeout_seconds,
            max_window=args.correction_max_window,
        )
    preload = getattr(service, "preload", None)
    if args.preload and callable(preload):
        preload()

    sample_results: list[dict[str, Any]] = []
    started_at = time.perf_counter()
    for index, sample in enumerate(samples, start=1):
        result = evaluate_sample(
            service,
            sample,
            corrector=corrector,
            sample_rate=args.sample_rate,
            sample_width_bytes=args.sample_width_bytes,
            channels=args.channels,
        )
        sample_results.append(result)
        rtf_display = f"{result['rtf']:.4f}" if result["rtf"] is not None else "n/a"
        print(
            f"[{index}/{len(samples)}] {sample.sample_name} "
            f"WER={result['wer']['rate']:.4f} CER={result['cer']['rate']:.4f} "
            f"RTF={rtf_display}"
        )

    total_elapsed_seconds = time.perf_counter() - started_at
    aggregate = aggregate_results(sample_results)
    payload = {
        "manifest_path": str(manifest_path),
        "backend": args.backend,
        "backend_model": args.backend_model or settings.stt_model_id,
        "model_path": args.model_path or settings.stt_model_path,
        "beam_size": args.beam_size if args.beam_size is not None else settings.stt_beam_size,
        "device": args.device or settings.stt_device,
        "compute_type": args.compute_type or settings.stt_compute_type,
        "apply_note_correction": args.apply_note_correction,
        "correction_backend": args.correction_backend or settings.note_transcript_correction_backend,
        "correction_model": args.correction_model or settings.note_transcript_correction_model,
        "run_label": args.run_label,
        "sample_rate": args.sample_rate,
        "sample_width_bytes": args.sample_width_bytes,
        "channels": args.channels,
        "sample_count": len(sample_results),
        "total_elapsed_seconds": round(total_elapsed_seconds, 4),
        "aggregate": aggregate,
        "samples": sample_results,
    }

    output_json_path = resolve_output_path(
        args.output_json,
        backend_name=args.backend,
        sample_count=len(sample_results),
        run_label=args.run_label,
    )
    output_json_path.parent.mkdir(parents=True, exist_ok=True)
    output_json_path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    output_jsonl_path = resolve_output_jsonl_path(args.output_jsonl, output_json_path=output_json_path)
    output_jsonl_path.parent.mkdir(parents=True, exist_ok=True)
    with output_jsonl_path.open("w", encoding="utf-8") as handle:
        for item in sample_results:
            handle.write(json.dumps(item, ensure_ascii=False))
            handle.write("\n")

    print("")
    print("KsponSpeech baseline 평가 완료")
    print(f"  manifest: {manifest_path}")
    print(f"  backend:  {args.backend}")
    print(f"  samples:  {len(sample_results)}")
    print(f"  avg WER:  {aggregate['avg_wer']}")
    print(f"  avg CER:  {aggregate['avg_cer']}")
    print(f"  avg RTF:  {aggregate['avg_rtf']}")
    print(f"  exact:    {aggregate['exact_match_rate']}")
    if aggregate.get("correction"):
        print(f"  corr WER: {aggregate['correction']['avg_wer']}")
        print(f"  corr CER: {aggregate['correction']['avg_cer']}")
        print(f"  corr ex:  {aggregate['correction']['exact_match_rate']}")
        print(f"  deltaWER: {aggregate['correction']['delta_avg_wer']}")
    print(f"  output:   {output_json_path}")
    print(f"  per-row:  {output_jsonl_path}")


if __name__ == "__main__":
    main()
