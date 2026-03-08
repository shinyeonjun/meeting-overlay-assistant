# CAPS 아키텍처 시각화 (ASCII)

> 이 문서는 프로젝트 핵심 구조를 ASCII 다이어그램으로만 정리한다.
> 최종 갱신: 2026-03-05

---

## 1. 전체 시스템 개요

```
╔═══════════════════════════════════════════════════════════════════════╗
║                     CAPS - Meeting AI Assistant                      ║
╠═══════════════════════════════════════════════════════════════════════╣
║                                                                       ║
║   ┌─────────────┐    ┌─────────────┐    ┌─────────────┐              ║
║   │  Overlay UI │    │  REST API   │    │  WebSocket  │              ║
║   │  (Frontend) │◄──►│  (FastAPI)  │◄──►│   (Audio)   │              ║
║   └──────┬──────┘    └──────┬──────┘    └──────┬──────┘              ║
║          │                  │                  │                      ║
║   ═══════╪══════════════════╪══════════════════╪══════════            ║
║          │            ┌─────┴─────┐            │                      ║
║          │            │  Services │            │                      ║
║          │            └─────┬─────┘            │                      ║
║          │                  │                  │                      ║
║          ▼                  ▼                  ▼                      ║
║   ┌─────────────────────────────────────────────────┐                ║
║   │              Domain Models / Enums              │                ║
║   └─────────────────────┬───────────────────────────┘                ║
║                         │                                            ║
║   ┌─────────────────────┴───────────────────────────┐                ║
║   │         Infrastructure (SQLite / Repos)         │                ║
║   └─────────────────────────────────────────────────┘                ║
╚═══════════════════════════════════════════════════════════════════════╝
```

---

## 2. 실시간 파이프라인 (system_audio 기준)

```
   [SYSTEM_AUDIO]
        │
        ▼
  ┌───────────────┐
  │ Audio Capture │  (Tauri + stream_live_audio_ws.py)
  └──────┬────────┘
         │  250ms chunk
         ▼
  ┌───────────────┐
  │ VAD / Segment │
  └──────┬────────┘
         │
         ▼
  ┌────────────────────────────────────────────────┐
  │      Hybrid STT (hybrid_local_streaming)      │
  │                                                │
  │  fast partial  ──► sherpa_onnx_streaming      │
  │  heavy final   ──► faster-whisper             │
  └───────────────┬────────────────────────────────┘
                  │
                  ▼
  ┌────────────────────────────────────────────────┐
  │ AudioPipelineService + StreamAlignmentManager  │
  │                                                │
  │  - segment_id 부여                             │
  │  - partial/final 정합성                        │
  │  - grace matching                              │
  │  - preview backpressure                        │
  └───────────────┬────────────────────────────────┘
                  │
                  ▼
  ┌────────────────────────────────────────────────┐
  │ TranscriptionGuard + Event Analyzer            │
  │  (질문/결정/액션/리스크 추출)                  │
  └───────────────┬────────────────────────────────┘
                  │
                  ▼
  ┌────────────────────────────────────────────────┐
  │ Overlay UI                                     │
  │  same segment_id: replace                      │
  │  new segment_id: commit + new line             │
  └────────────────────────────────────────────────┘
```

---

## 3. 회의 후 파이프라인 (Post-Meeting Path)

```
   [WAV_FILE]
        │
        ▼
  ┌──────────────────┐
  │ AudioPreprocessor │
  │  bypass / deepfilter │
  └────────┬─────────┘
           │
           ▼
  ┌──────────────────────┐
  │ Speaker Diarizer     │
  │  unknown / pyannote  │
  └──────────┬───────────┘
             │
             ▼
  ┌──────────────────────┐
  │ faster-whisper       │
  │ (구간별 재전사)      │
  └──────────┬───────────┘
             │
             ▼
  ┌──────────────────────────────┐
  │ Markdown / 리포트 정리       │
  │ 질문/결정/액션/리스크 구조화 │
  └──────────────────────────────┘
```

---

## 4. 마이크 경로 (현재 운영)

```
   [MIC]
     │
     ▼
┌──────────────────────────────────┐
│ Tauri live audio stream          │
│ (backend/scripts/stream_live...) │
└─────────────┬────────────────────┘
              │
              ▼
┌──────────────────────────────────┐
│ backend STT                      │
│ (현재: faster_whisper_streaming) │
└─────────────┬────────────────────┘
              │
              ▼
┌────────────────────────────┐
│ Overlay UI + Event 연동    │
└────────────────────────────┘
```

---

## 5. 서비스 레이어 구조

```
┌──────────────────────────────────────────────────────────────┐
│                         Service Layer                        │
├──────────────────────────────────────────────────────────────┤
│ audio/pipeline      -> audio_pipeline_service               │
│                        stream_alignment_manager              │
│ audio/stt           -> hybrid / sherpa / faster-whisper     │
│ audio/segmentation  -> speech_segmenter / silero_vad        │
│ audio/filters       -> transcription_guard / content_gate    │
│ analysis            -> rule + llm analyzers                 │
│ events              -> meeting_event_service                 │
│ reports             -> report_service + markdown builder     │
└──────────────────────────────────────────────────────────────┘
```

---

## 6. 실시간 후보 5개 모델 비교 (요약)

```
┌───────────────────────────────────────────────────────────────────────┐
│ system_audio / 15초 샘플 기준                                        │
├───────────────────────────────────────────────────────────────────────┤
│ faster_whisper_streaming   partial 4.71s / final 5.23s / RTF 2.93   │
│ moonshine_streaming        partial 1.07s / final 2.51s / 정확도 탈락 │
│ simulstreaming             partial 1.24s / final 15.0s / RTF 1.93    │
│ sherpa_onnx_streaming      partial 0.06s / final 0.97s / RTF 0.34    │
│ sensevoice_small_streaming partial 0.22s / final 41.99s / RTF 3.83   │
├───────────────────────────────────────────────────────────────────────┤
│ 결론:                                                                │
│   fast partial = sherpa                                              │
│   final 보정   = faster-whisper                                      │
│   (single-engine보다 hybrid가 현실적)                                │
└───────────────────────────────────────────────────────────────────────┘
```

---

## 7. 정합성 상태 머신 (segment_id)

```
partial(rev1) ─► partial(rev2) ─► partial(rev3)
    │               │                 │
    └──── same segment_id 유지 ───────┘
                      │
                      ▼
                 final 도착
                      │
      ┌───────────────┴────────────────┐
      │ alignment=matched_active_preview │
      │ alignment=grace_matched_recent   │
      │ alignment=standalone_final       │
      └──────────────────────────────────┘
```

---

## 8. 설정 흐름 (.env → Config → Policy → Factory)

```
.env
 ├─ STT_BACKEND_SYSTEM_AUDIO=hybrid_local_streaming_sherpa
 ├─ STT_BACKEND=faster_whisper_streaming
 └─ STT_MODEL_ID=deepdml/faster-whisper-large-v3-turbo-ct2
        │
        ▼
config.py / audio_source_profiles.json / media_service_profiles.json
        │
        ▼
dependencies.py
 └─ source별 AudioPipelineService 조립
        │
        ▼
speech_to_text_factory.py
 └─ partial 엔진 + final 엔진 생성 및 주입
```

검토 경로:
- `mic`에 Web Speech API를 붙이는 선택지는 별도 실험 트랙으로 유지한다.
