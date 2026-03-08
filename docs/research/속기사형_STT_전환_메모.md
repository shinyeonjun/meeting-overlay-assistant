# 속기사형 STT 전환 메모

> 목적: 회의 중 UX(빠른 반응)와 최종 문장 품질(정확도)을 동시에 만족시키는 운영 기준을 정리한다.  
> 최종 갱신: 2026-03-05

---

## 1. 목표 UX

속기사형 UX의 핵심은 `빠른 partial`과 `안정적인 final`의 분리다.

```text
partial: 타이핑처럼 빠르게 갱신
final  : 문장 단위로 교체 확정
```

---

## 2. 현재 구현 상태

- 마이크(`mic`): Web Speech API 기본 경로 운영, backend STT(`faster_whisper_streaming`) fallback 유지
- 백엔드: `hybrid_local_streaming` 적용 완료
  - partial: `sherpa_onnx_streaming`
  - final: `faster-whisper`
- 정합성: `segment_id` + `revision` 기반 partial/final 교체 적용
- 프론트: 같은 `segment_id`는 replace, 새 `segment_id`는 commit

---

## 3. 현재 문제와 해석

- partial은 빠르지만 표현이 흔들릴 수 있다.
- final은 더 정확하지만 특정 구간에서 치환/왜곡이 남는다.
- 따라서 문제의 중심은 엔진 교체보다 `정합성/튜닝 파라미터`다.

---

## 4. 튜닝 우선순위

1. `standalone_final` 비율 줄이기  
2. final 신뢰도 필터 임계값 재조정 (`short_final_low_confidence` 과차단 방지)  
3. 도메인 키워드(예: 게임/개발 용어) 편향 실험  
4. endpoint 및 grace window 파라미터 보정

---

## 5. 확인 지표

- `first_partial_latency`
- `first_final_latency`
- `standalone_final` 비율
- partial 교체 안정성(`segment_id` 정합률)
- 최종 문장 품질(WER/CER 또는 수동 샘플 평가)

---

## 6. 관련 파일

- [audio_pipeline_service.py](/D:/caps/backend/app/services/audio/pipeline/audio_pipeline_service.py)
- [stream_alignment_manager.py](/D:/caps/backend/app/services/audio/pipeline/stream_alignment_manager.py)
- [hybrid_streaming_speech_to_text_service.py](/D:/caps/backend/app/services/audio/stt/hybrid_streaming_speech_to_text_service.py)
- [벤치마크_비교표.md](/D:/caps/docs/research/벤치마크_비교표.md)
