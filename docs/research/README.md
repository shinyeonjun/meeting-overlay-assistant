# research 문서 안내

`research/`는 현재 제품 구현 기준이 아니라, 조사와 실험의 배경 자료를 모아두는 곳입니다.

여기 문서는 주로 아래 목적에 씁니다.

- 특정 모델이나 전략을 왜 선택했는지 배경을 남김
- 부하 테스트, 벤치마크, 비교 결과를 기록
- 구조 개선 아이디어나 전환 메모를 남김

공식 기준이 필요하면 아래를 먼저 봅니다.

- 구조 기준: `docs/architecture/`
- 제품 기준: `docs/product/`

## 현재 유지하는 문서

- [실시간 STT 파이프라인 평가 (2026-10)](실시간_STT_파이프라인_평가.md)
- [실시간 STT 실서버 검증 (2026-10-13)](실시간_STT_실서버_검증.md)
- [회색 자막 Nemotron 전환 실서버 검증 (2026-10-13)](실시간_STT_회색자막_Nemotron_검증.md)
- [live runtime actual backend 부하 테스트](live_runtime_actual_backend_load_test.md)
- [live runtime 부하 테스트](live_runtime_load_test.md)
- [벤치마크 비교표](벤치마크_비교표.md)
- [로컬 실시간 STT 조사](로컬_실시간_STT_조사.md)
- [로컬모델 선정표](로컬모델_선정표.md)
- [하이브리드 STT 전략](하이브리드_STT_전략.md)

## archive로 보낸 문서

- [속기사형 STT 전환 메모](../archive/research/속기사형_STT_전환_메모.md)

## 추천 읽기 순서

1. [실시간 STT 파이프라인 평가 (2026-10)](실시간_STT_파이프라인_평가.md)
2. [실시간 STT 실서버 검증 (2026-10-13)](실시간_STT_실서버_검증.md)
3. [회색 자막 Nemotron 전환 실서버 검증 (2026-10-13)](실시간_STT_회색자막_Nemotron_검증.md)
4. [live runtime actual backend 부하 테스트](live_runtime_actual_backend_load_test.md)
5. [live runtime 부하 테스트](live_runtime_load_test.md)
6. [벤치마크 비교표](벤치마크_비교표.md)
7. [로컬모델 선정표](로컬모델_선정표.md)
8. [하이브리드 STT 전략](하이브리드_STT_전략.md)

## 지금 main 구성의 측정 요약

RTX 5070 Laptop(8GB) 한 대, FLEURS 한국어 낭독 음성 기준이다. 정확도는 `100% − CER`이다.

| 항목 | 값 | 출처 |
|---|---|---|
| 확정 자막 정확도 (100초 스트림 6개 / 30분 연속) | 91.5% / 92.0% | Nemotron 검증 4장 |
| 회색 자막 정확도 | 86.9% (sherpa 60.9%) | Nemotron 검증 4.1 |
| 말 시작 → 첫 회색 자막 | 평균 548ms, p90 973ms | Nemotron 검증 4.1 |
| 말 끝 → 확정 자막 도착 | 중앙값 848ms, p90 1,046ms | Nemotron 검증 4.1 |
| 늦은 확정 (30분) | 0개 | Nemotron 검증 4.2 |
| 서버 / GPU 메모리 | 약 2.3GB / 약 4.5GB, 30분에 각각 +48MB / +42MB | Nemotron 검증 4.2 |
| 동시 세션 | 2개까지 밀림 없음 (오프라인 측정), 실서버 미측정 | 파이프라인 평가 5.7 |

아직 재지 않은 것: 실서버 동시 세션 2개, 1시간 이상 메모리 추이, Tauri 오버레이 실기 끝단 지연, 실제 마이크 입력, 다른 프로그램과 GPU 공유.

## 사용 원칙

1. 실험/조사 결과는 `research/`에 둡니다.
2. 현재 제품 기준으로 확정된 내용은 `architecture/`, `product/`에 반영합니다.
3. 더 이상 직접 참고하지 않는 조사 메모는 `archive/`로 옮깁니다.
