# STT Experiments

프로덕션 경로가 아닌 STT 실험, 벤치마크, probe 스크립트를 모아두는 공간이다.

포함 대상:
- 백엔드별 정확도 벤치마크
- 실시간 STT latency 비교
- NPU/로컬 모델 probe
- acceptance runner

운영 스크립트는 `backend/scripts`에 두고, 여기는 모델/파이프라인 비교 실험만 둔다.

## 주요 스크립트

- `benchmark_stt_backends.py`
  - WAV 기준으로 backend별 WER/CER를 비교한다.
- `benchmark_realtime_stt.py`
  - partial / final 첫 emit 시간과 전체 RTF를 비교한다.
- `benchmark_sherpa_streaming.py`
  - `sherpa-onnx` streaming 모델을 wrapper backend 형식으로 실행한다.
- `benchmark_sherpa_streaming.ps1`
  - Windows 개발 환경에서 `sherpa_onnx_streaming` 벤치마크를 바로 호출하는 래퍼다.
- `run_stt_acceptance.py`
  - 기준 샘플 세트에 대해 acceptance 체크를 수행한다.

## sherpa-onnx 벤치마크

속기사형 STT 후보는 `sherpa-onnx` 같은 진짜 streaming ASR로 보고 있다.
현재 프로젝트 기준으로는 `system_audio` 실시간 자막 전용 후보로만 평가한다.

실행 예시:

```powershell
powershell -ExecutionPolicy Bypass -File .\backend\experiments\stt\benchmark_sherpa_streaming.ps1 `
  -Wav .\tests\video\test_16k_mono_15s.wav `
  -ModelPath .\backend\models\stt\sherpa-onnx-ko-streaming `
  -Source system_audio `
  -Warmup
```

직접 Python으로 돌릴 수도 있다.

```powershell
.\venv\Scripts\python.exe .\backend\experiments\stt\benchmark_realtime_stt.py `
  --wav .\tests\video\test_16k_mono_15s.wav `
  --source system_audio `
  --backend sherpa_onnx_streaming `
  --backend-model sherpa_onnx_streaming=.\backend\models\stt\sherpa-onnx-ko-streaming `
  --warmup
```

## SenseVoice-Small 벤치마크

`SenseVoice-Small`은 한국어 지원과 저지연 추론이 강점이라 다음 후보로 비교한다.
현재 경로는 pseudo-streaming 래퍼다. 즉, 누적 오디오를 짧은 간격으로 다시 전사해서
partial 증가 패턴과 첫 partial / final 지연을 비교한다.

실행 예시:

```powershell
.\venv\Scripts\python.exe .\backend\experiments\stt\benchmark_realtime_stt.py `
  --wav .\tests\video\test_16k_mono_15s.wav `
  --source system_audio `
  --backend sensevoice_small_streaming `
  --backend-model sensevoice_small_streaming=.\backend\models\stt\SenseVoiceSmall `
  --warmup
```

비교 실행 예시:

```powershell
powershell -ExecutionPolicy Bypass -File .\backend\experiments\stt\compare_streaming_candidates.ps1 `
  -Wav .\tests\video\test_16k_mono_15s.wav `
  -SherpaModelPath .\backend\models\stt\sherpa-onnx-streaming-zipformer-korean-2024-06-16 `
  -SenseVoiceModelPath .\backend\models\stt\SenseVoiceSmall `
  -Source system_audio `
  -Warmup `
  -OutputJson .\temp\streaming_compare.json
```

## 실험 원칙

- `meeting/mic`와 `system_audio`는 같은 엔진 전략으로 억지로 묶지 않는다.
- `system_audio`는 속기사형 incremental caption UX를 우선한다.
- 하드코딩 문구 필터는 마지막 안전장치로만 두고, 본체는 streaming ASR 성능으로 해결한다.
- `faster-whisper`는 final 보정 후보로 유지하고, `system_audio` 실시간 표시는 별도 streaming 엔진으로 평가한다.
