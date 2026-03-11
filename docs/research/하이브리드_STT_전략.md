# 하이브리드 STT 전략

## 전략 요약

현재 STT 전략은 한 모델로 live와 report를 모두 해결하지 않는다.

대신 다음처럼 나눈다.

- live partial: 빠름 우선
- archive/report final: 정확도 우선

## 현재 구조

### live 경로

- Sherpa 기반 partial / fast-final 성격의 중간 단계
- 메인 오버레이 자막과 누적 transcript에 사용

### archive 경로

- Faster-Whisper final
- DB 저장, 리포트 생성, PDF 생성에 사용

## 왜 하이브리드가 필요한가

### 단일 streaming 모델만 쓰면

- 실시간 partial은 빠를 수 있지만
- 최종 정확도가 낮아 리포트 품질이 떨어진다

### Whisper만 쓰면

- 최종 품질은 좋지만
- 실시간 live 첫 지연과 final 지연이 커진다

따라서 한 경로에서 두 요구사항을 모두 만족시키기 어렵다.

## 현재 구현 철학

- live는 빠르고 덜 거슬리는 자막
- report는 고정밀 transcript 기반 최종 문서

이 철학은 API, UI, 저장 구조, 리포트 정책에도 반영되어 있다.

## 향후 개선 포인트

- `stability` 기반 live 렌더 고도화
- `fast_final` 중간 계층 강화
- `early_eou / final_eou` 분리
- 관측 지표 강화
