# research 문서 안내

`research/`는 현재 제품의 공식 기준 문서가 아니라, 조사·실험·비교 결과를 모아두는 작업 메모 공간입니다.

여기에는 주로 아래 내용을 둡니다.

- 모델이나 전략을 왜 선택했는지에 대한 배경
- 부하 테스트, 벤치마크, 비교 결과
- 구조 전환 아이디어와 실험 메모
- 하드웨어 자원 사용과 병목 분석

공식 기준이 필요하면 아래 문서를 먼저 봅니다.

- 구조 기준: `docs/architecture/`
- 제품 기준: `docs/product/`

## 현재 유지하는 문서

- [live runtime actual backend 부하 테스트](live_runtime_actual_backend_load_test.md)
- [live runtime 부하 테스트](live_runtime_load_test.md)
- [벤치마크 비교표](벤치마크_비교표.md)
- [로컬 실시간 STT 조사](로컬_실시간_STT_조사.md)
- [로컬모델 선정표](로컬모델_선정표.md)
- [런타임 자원, 병목, 검증 정리](런타임_자원_병목_및_검증_정리.md)
- [하이브리드 STT 전략](하이브리드_STT_전략.md)

## archive로 보낸 문서

- [속기사형 STT 전환 메모](../archive/research/속기사형_STT_전환_메모.md)

## 추천 읽기 순서

1. [런타임 자원, 병목, 검증 정리](런타임_자원_병목_및_검증_정리.md)
2. [live runtime actual backend 부하 테스트](live_runtime_actual_backend_load_test.md)
3. [live runtime 부하 테스트](live_runtime_load_test.md)
4. [벤치마크 비교표](벤치마크_비교표.md)
5. [로컬모델 선정표](로컬모델_선정표.md)
6. [하이브리드 STT 전략](하이브리드_STT_전략.md)

## 사용 원칙

1. 실험과 조사 결과는 `research/`에 둡니다.
2. 현재 제품 기준으로 확정된 내용은 `architecture/`, `product/`에 반영합니다.
3. 더 이상 직접 참고하지 않는 조사 메모는 `archive/`로 옮깁니다.
