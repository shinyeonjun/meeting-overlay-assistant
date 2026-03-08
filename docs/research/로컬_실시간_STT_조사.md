# 로컬 실시간 STT 조사

> 목적: `system_audio` 실시간 자막 경로를 실제 벤치마크 결과 기준으로 정리한다.  
> 최종 갱신: 2026-03-05

---

## 0. 범위

- 이 문서는 `system_audio` 로컬 STT 경로만 다룬다.
- `mic`는 현재 Web Speech API를 기본 경로로 사용하며, backend STT는 fallback 경로로 유지한다.

## 1. 최종 결론

- 단일 엔진으로 `속도 + 품질`을 동시에 만족시키기 어려웠다.
- 현재 최적 경로는 하이브리드다.
  - fast partial: `sherpa_onnx_streaming`
  - heavy final: `faster-whisper`
- 정합성은 `segment_id` 기반으로 관리한다.

---

## 2. 실시간 후보 비교 (동일 샘플)

테스트 샘플: `D:\caps\tests\video\test_16k_mono_15s.wav`

| 모델/엔진 | first_partial | first_final | RTF(total) | 판정 |
|---|---:|---:|---:|---|
| `faster_whisper_streaming` | 4.7097s | 5.2344s | 2.9344 | partial 실시간성 부족 |
| `moonshine_streaming` | 1.07s | 2.51s | - | 한국어 정확도 부족 |
| `simulstreaming` | 1.24s | 15.0s | 1.932 | final 지연 과대 |
| `sherpa_onnx_streaming` | 0.0622s | 0.9698s | 0.3401 | fast partial 적합 |
| `sensevoice_small_streaming` (CPU) | 0.2231s | 41.9867s | 3.8314 | final 지연 과대 |

추가 튜닝(`sherpa`):
- `modified_beam_search + endpoint 조정` 이후
  - first_partial: `0.0527s`
  - first_final: `0.1707s`
  - RTF(total): `0.1964`

---

## 3. 현재 적용 구조

```text
system_audio
  -> AudioPipelineService
  -> hybrid_local_streaming
     -> partial: sherpa_onnx_streaming
     -> final:   faster_whisper
  -> segment_id 기준 partial/final 교체
```

현재는 `속도(부분자막)`와 `최종 가독성(확정문)`을 분리해 운영한다.

---

## 4. 남은 튜닝 과제

1. `system_audio` final 품질 개선 (오인식 치환 감소)
2. `standalone_final` 비율 축소 (grace matching 강화)
3. 도메인 편향(핫워드/키워드) 적용 여부 실험

---

## 5. 참고 문서

- [벤치마크_비교표.md](/D:/caps/docs/research/벤치마크_비교표.md)
- [로컬모델_선정표.md](/D:/caps/docs/research/로컬모델_선정표.md)
- [하이브리드_STT_전략.md](/D:/caps/docs/research/하이브리드_STT_전략.md)
