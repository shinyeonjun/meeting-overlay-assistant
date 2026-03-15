# WebSocket Contracts

이 디렉터리는 실시간 통신 payload 계약을 정리한다.

현재 가장 중요한 경로는 live caption payload다.

## 포함 범위

- 실시간 자막 payload
- 실시간 질문 이벤트 payload
- `partial / fast_final / final / late_final`
- `low / medium / final` stability

## 경계 원칙

1. WebSocket은 live UX를 위한 채널이다.
2. 최종 정본은 서버 transcript / event / report가 맡는다.
3. live payload는 너무 무겁지 않게 유지한다.
4. `late_final`은 버리는 값이 아니라 늦게 도착한 확정 자막이다.
