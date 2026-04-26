# API Contracts

이 디렉터리는 CAPS의 HTTP API 계약과 JSON Schema를 관리한다.

## 현재 범위

- `session`
  - 세션 draft 생성, 시작, 종료, overview, 참여자 조회
- `auth`
  - bootstrap, login, logout, me, auth config
- `report / share`
  - 회의록 목록, 생성 상태, 공유함, 공유받은 회의록함
- `event`
  - 이벤트 목록, 수정, 상태 전이
- `history`
  - timeline, carry-over, retrieval brief
- `retrieval`
  - hybrid retrieval 검색
- `context`
  - account, contact, context thread
- `runtime`
  - readiness, monitor

## 현재 기준 원칙

- 사용자 식별자는 `email`이 아니라 `login_id`다.
- 세션 입력 정본은 `primary_input_source`와 `actual_active_sources`다.
- 회의록 공유는 유지하지만 별도 감사 로그 API는 없다.
- 이벤트 API는 외부 계약상 `created_at_ms`, `updated_at_ms`를 유지할 수 있다.
  - PostgreSQL 내부 저장은 `TIMESTAMPTZ`를 쓴다.
- retrieval은 `pgvector` 기반이지만 API 계약은 일반 검색 응답 형태를 유지한다.

## 주요 파일

- `session-auth-contract.md`
- `report-event-contract.md`
- `context-runtime-contract.md`
- `session.schema.json`
- `auth.schema.json`
- `report.schema.json`
- `events.schema.json`
- `history.schema.json`
- `retrieval.schema.json`
- `context.schema.json`
- `runtime.schema.json`
- `session-overview.schema.json`
- `final-report-status.schema.json`

## 파일 종류

- `*.md`
  - 사람이 읽는 설명 문서
- `*.schema.json`
  - 테스트와 계약 검증에 쓰는 JSON Schema

## 운영 규칙

- 구현이 바뀌면 설명 문서와 schema를 같이 갱신한다.
- enum 문자열은 `shared/enums/catalog.json` 기준으로 맞춘다.
- 서버와 클라이언트는 같은 이름과 같은 의미를 쓰도록 유지한다.
