# 하이브리드 STT 전략

## 한 줄 요약

처음에는 `NPU 기반 회의 어시스턴트`를 목표로 했지만,
실제 벤치마크 결과 현재 STT는 `GPU가 더 현실적`이었습니다.

따라서 현재 시스템은:

- `GPU`를 실사용 STT 주 경로로 두고
- `NPU`는 저전력 상시 감지 및 연구 트랙으로 재배치합니다.
- 입력 소스별로 경로를 분리해 운영합니다.
  - `mic`: backend STT(`faster_whisper_streaming`) 운영
  - `system_audio`: 하이브리드 STT (sherpa partial + faster-whisper final)

## 왜 이렇게 바꿨는가

캡스톤/연구 관점에서 중요한 건 `NPU만 썼다`가 아닙니다.

더 강한 메시지는 이겁니다.

> GPU와 NPU를 같은 조건에서 비교했고, 그 결과를 바탕으로 실제 역할을 분리해 설계했다.

이 포지셔닝이 좋은 이유:

- 숫자 근거가 있음
- 단순 구현이 아니라 설계 판단이 들어감
- 연구 인사이트로 설명 가능
- 이후 확장성도 자연스럽게 이어짐

## 실제 벤치마크 결과

동일 샘플 기준:

| 항목 | faster-whisper GPU | AMD Whisper NPU |
|---|---:|---:|
| WER | 0.1714 | 0.3429 |
| CER | 0.1140 | 0.1754 |
| RTF | 0.2697 | 1.1494 |
| First Guarded Latency | 2.8243s | 14.3790s |
| Peak RSS | 약 468MB | 약 3.18GB |

현재 결과만 보면:

- 정확도: GPU 우세
- 속도: GPU 우세
- 메모리: GPU 우세

즉 현 단계의 실사용 STT 주력은 `GPU`가 맞습니다.

## 역할 분리

| 역할 | 엔진 | 설명 |
|---|---|---|
| 마이크 실시간 STT | faster_whisper_streaming | 현재 운영 경로 |
| system_audio 실시간 STT | GPU 하이브리드 (`sherpa` + `faster-whisper`) | 속도/품질 균형 |
| 상시 감지 / 전단 필터 | NPU | 저전력, always-on 연구 가치 |
| 회의 후 분석 / 문서화 | 로컬 LLM (`Ollama`) | 구조화 문서와 요약 품질 확보 |

참고:
- Web Speech API는 마이크 경로의 기본값으로 운영하고, backend STT를 fallback으로 둔다.

## 발표에서 이렇게 말하면 좋다

### 짧은 버전

> 처음에는 NPU 중심으로 설계했지만, 실제 벤치마크 결과 현시점 STT는 GPU가 더 우세했습니다. 그래서 GPU를 주 경로로, NPU는 저전력 상시 감지 연구 트랙으로 재배치했습니다.

### 긴 버전

> 본 프로젝트는 단순히 특정 하드웨어를 사용하는 데 목적이 있지 않습니다. GPU와 NPU를 동일 조건에서 비교해 실제 회의 시스템에서 어떤 역할 분담이 가장 합리적인지 검증하는 데 목적이 있습니다. 실험 결과, 실시간 STT는 GPU가 정확도와 지연 시간에서 우세했고, NPU는 저전력 상시 감지와 향후 최적화 연구 측면에서 의미가 있었습니다. 따라서 최종 설계는 GPU-NPU 하이브리드 구조를 채택했습니다.

## 연구 인사이트

이 프로젝트에서 NPU는 실패한 선택이 아니라, 다음 질문을 만드는 연구 대상입니다.

- 왜 현 시점 STT는 GPU가 더 유리한가
- NPU는 어떤 전처리/감지 레이어에서 더 유효한가
- 하드웨어별 역할 분리를 하면 시스템 전체 효율이 어떻게 달라지는가

즉 차별성은 `NPU를 썼다`가 아니라:

> 어떤 작업은 GPU가, 어떤 작업은 NPU가 더 적합한지 실제 데이터로 설명했다.

## 다음 연구 방향

1. NPU 기반 `always-on VAD` 또는 음성 감지 전단 실험
2. ~~`Moonshine` 같은 초경량 모델과의 추가 비교~~ → **2026-03-04 완료:** `moonshine/tiny-ko` 벤치마크 결과 WER 0.86으로 탈락
3. ~~`Whisper-Streaming / Local Agreement` 기반 partial transcript UX 실험~~ → **2026-03-05 1차 완료:** `segment_id` 기반 partial/final 정합 파이프라인 반영
4. ~~`system_audio` 실시간 후보 다중 비교~~ → **2026-03-05 완료:** faster-whisper / moonshine / simulstreaming / sherpa / sensevoice 비교
5. 장시간 회의에서 전력 소모와 발열 비교
6. `standalone_final` 비율 기반 튜닝(정합성 지표 개선)

> 상세 벤치마크 결과: [벤치마크_비교표.md](벤치마크_비교표.md)
