# 로컬 실시간 STT 조사

## 조사 목적

이 프로젝트는 네트워크 의존도를 줄이고 로컬 환경에서 회의 자막을 제공하는 것을 목표로 한다.  
따라서 조사 기준은 단순 정확도가 아니라 다음을 함께 본다.

- 첫 partial 지연
- 첫 final 지연
- 전체 RTF
- 메모리 사용량
- 한국어 품질
- 로컬 배포 난이도

## 후보군

### 1. Faster-Whisper

장점:
- 최종 정확도가 높다
- 로컬 리포트 생성과 archive-final에 적합하다

단점:
- 실시간 live final 용도로는 첫 지연이 크다
- partial 중심 UX에는 단독 사용이 어렵다

### 2. Sherpa-ONNX streaming

장점:
- 실시간 partial 응답성이 좋다
- 현재 프로젝트의 live 자막 경로에 적합하다

단점:
- 최종 리포트용 정확도를 단독으로 맡기기 어렵다

### 3. Whisper Streaming / SimulStreaming / Moonshine

조사 및 벤치마크 결과:
- partial 응답성은 일부 장점이 있어도 최종 정확도나 안정성이 아쉬웠다
- 현재 프로젝트의 메인 경로로 채택하기엔 trade-off가 나빴다

## 현재 결론

실시간 STT는 한 모델로 해결하는 방식보다, 역할을 나누는 방식이 더 현실적이다.

- live partial: Sherpa
- archive/report final: Faster-Whisper

즉 `하이브리드 STT` 전략이 현재 최선이다.
