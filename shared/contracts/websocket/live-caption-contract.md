# Live Caption Contract

이 문서는 실시간 자막 WebSocket payload의 의미를 설명한다.

## 목적

- 클라이언트가 live caption을 같은 방식으로 해석하도록 만든다.
- `preview`, `live_final`, `archive_final`, `late_archive_final`을 UI에서 다르게 다룰 수 있게 한다.

## payload 필드

- `session_id`
  - 현재 세션 식별자
- `input_source`
  - `mic`, `system_audio`, `mic_and_audio`, `file`
- `utterances`
  - 자막 후보 목록
- `events`
  - live 질문 이벤트 목록
- `error`
  - 스트림 오류 메시지

## utterance 해석 규칙

- `kind=preview`
  - 아직 흔들릴 수 있는 임시 실시간 자막
- `kind=live_final`
  - preview보다 안정적이지만 여전히 실시간 보조값
- `kind=archive_final`
  - 정상적으로 제때 도착한 확정 자막
- `kind=late_archive_final`
  - 늦게 도착해서 현재 자막을 덮지 않고 transcript/history에만 반영해야 하는 확정 자막

- `stability=low`
  - 흔들리는 preview
- `stability=medium`
  - `live_final` 수준
- `stability=final`
  - 최종 확정 수준

## UI 권장 해석

- `preview`
  - 현재 발화 미리보기
- `live_final`
  - 메인 자막 후보
- `archive_final`
  - 메인 자막과 transcript 둘 다 반영
- `late_archive_final`
  - 메인 자막은 유지하고 transcript/history만 보강
