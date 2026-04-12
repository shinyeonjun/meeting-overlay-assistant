# shared

`shared/`는 서버와 클라이언트가 같은 의미를 바라보게 만드는 계약 기준 레이어다.

지금 단계에서는 실제 공용 런타임 패키지보다 아래 세 가지를 먼저 고정한다.

1. API / WebSocket 계약 문서와 JSON Schema
2. 공통 enum catalog
3. 서버와 클라이언트가 같이 참고할 의미 규칙

## 하위 디렉터리

- `contracts/`
  - HTTP API와 WebSocket payload 계약
- `enums/`
  - 서버와 클라이언트가 공유하는 상태값 목록
- `schemas/`
  - 예전 설명 문서 자리. 신규 계약은 추가하지 않음

## 현재 상태

- `shared`는 문서 중심 계약 레이어다.
- 서버와 클라이언트 구현은 아직 각 코드베이스 안에 있지만, payload 의미는 `shared` 기준으로 맞춘다.
- 목표는 드리프트를 막는 최소 기준선을 먼저 세우는 것이다.

## 현재 올라간 범위

- `session_status`, `workspace_role`, `event_type`, `event_state`
- `history_scope`, `report_format`, `final_report_status`
- `live_utterance_kind`, `live_utterance_stability`
- `report_share_permission`, `auth_token_type`
- session / auth / report / event / context / runtime / websocket 계약

## 다음 단계

1. shared 계약 기준으로 서버/클라이언트 adapter를 더 단순화
2. 남은 레거시 설명 문서를 `contracts/` 기준으로 정리
3. 필요 시 실제 공용 타입/상수 코드까지 승격
