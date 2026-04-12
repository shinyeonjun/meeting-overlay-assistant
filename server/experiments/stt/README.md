# STT 실험 디렉터리 안내

이 디렉터리는 서버 기준 STT 실험과 벤치마크 자산을 모아두는 공간이다. 제품 런타임 코드와는 분리해서 취급한다.

## 목적

- STT 백엔드 후보 비교
- 실시간 / 배치 벤치마크 실행
- provider 가용성 probe
- acceptance 스크립트 유지
- 채택 판단 근거 수집

즉 이 디렉터리의 스크립트는 제품 기능 그 자체가 아니라, 제품 설계를 뒷받침하는 실험 자산이다.

## 주요 스크립트

- `benchmark_live_stream_runtime.py`
  - synthetic pipeline 기준 live runtime 구조 부하 테스트
- `benchmark_live_stream_runtime_actual.py`
  - 현재 settings 기반 실제 STT backend를 live runtime에 붙인 actual 부하 테스트
- `benchmark_realtime_stt.py`
  - 실시간 STT 백엔드 비교
- `benchmark_sherpa_streaming.py`
  - Sherpa-ONNX 스트리밍 벤치마크
- `benchmark_stt_backends.py`
  - 여러 STT 백엔드 종합 비교
- `benchmark_sensevoice_small.py`
  - SenseVoice 계열 실험
- `compare_streaming_candidates.ps1`
  - 스트리밍 후보 비교 실행 보조
- `run_stt_acceptance.py`
  - STT acceptance 실행
- `probe_moonshine_npu.py`
  - NPU 경로 가용성 확인
- `probe_sherpa_provider_support.py`
  - Sherpa provider 지원 여부 확인

## 운영 원칙

1. 실험 결과는 가능하면 JSON artifact로 남긴다.
2. 실험 코드는 제품 런타임 import 경로에 직접 묶지 않는다.
3. 채택 판단은 문서로 다시 남긴다.
4. 제품 코드에 반영된 최종 결정은 `docs/research/` 문서와 함께 관리한다.

## 현재 기준 역할

현재 프로젝트의 STT 역할 분리는 아래와 같다.

- live partial / fast response
  - Sherpa-ONNX 계열
- archive final / 고정밀 기록
  - Faster-Whisper GPU 계열

이 디렉터리는 이 판단을 계속 검증하고 갱신하기 위한 실험 공간이다.
