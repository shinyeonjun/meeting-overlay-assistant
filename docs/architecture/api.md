# API 문서

이 문서는 현재 코드 기준의 HTTP / WebSocket 인터페이스를 설명한다. 기본 prefix는 `/api/v1`이다.

## 인증 정책

- `AUTH_ENABLED=false`면 대부분의 API가 개발 모드로 열린다.
- `AUTH_ENABLED=true`면 HTTP와 WebSocket 모두 Bearer 토큰이 필요하다.
- 목록 API는 `scope=mine|all`을 지원한다.
  - `mine`: 현재 사용자 기준
  - `all`: `owner`, `admin`만 허용

## 1. Auth API

### `GET /api/v1/auth/config`

- 목적: 로그인 필요 여부와 bootstrap 필요 여부 조회
- 주요 응답
  - `auth_enabled`
  - `bootstrap_required`
  - `user_count`

### `POST /api/v1/auth/bootstrap-admin`

- 목적: 초기 관리자 계정 생성
- 주요 요청
  - `login_id`
  - `password`
  - `display_name`

### `POST /api/v1/auth/login`

- 목적: `login_id + password` 로그인
- 주요 응답
  - `access_token`
  - `user`
  - `workspace`

### `GET /api/v1/auth/me`

- 목적: 현재 로그인 사용자와 workspace 정보 조회

### `POST /api/v1/auth/logout`

- 목적: 현재 세션 토큰 만료

## 2. Session API

### `GET /api/v1/sessions/`

- 목적: 최신 세션 목록 조회
- 쿼리
  - `scope=mine|all`
  - `account_id`
  - `contact_id`
  - `context_thread_id`
  - `limit`

### `POST /api/v1/sessions/`

- 목적: 세션 draft 생성
- 예시

```json
{
  "title": "주간 제안 미팅",
  "mode": "meeting",
  "primary_input_source": "system_audio",
  "account_id": "account-...",
  "contact_id": "contact-...",
  "context_thread_id": "context-thread-...",
  "participants": ["김현우", "박서연"]
}
```

- 주요 응답
  - `id`
  - `title`
  - `status`
  - `account_id`
  - `contact_id`
  - `context_thread_id`
  - `participants`
  - `participant_links`
  - `primary_input_source`
  - `actual_active_sources`

### `POST /api/v1/sessions/{session_id}/start`

- 목적: draft 세션을 `running`으로 전이

### `POST /api/v1/sessions/{session_id}/end`

- 목적: 세션 종료
- 메모: 세션 종료와 리포트 생성은 분리되어 있고, 종료 후 `report_generation_job`이 생성된다.

### `GET /api/v1/sessions/{session_id}/overview`

- 목적: 진행 중 세션 overview 조회
- 주요 응답
  - `session`
  - `current_topic`
  - `questions`
  - `decisions`
  - `action_items`
  - `risks`
  - `metrics`

## 3. Context API

prefix: `/api/v1/context`

- `GET /accounts`, `POST /accounts`
- `GET /contacts`, `POST /contacts`
- `GET /threads`, `POST /threads`

주요 필터:

- `account_id`
- `contact_id`
- `limit`

## 4. History API

prefix: `/api/v1/history`

### `GET /timeline`

- 목적: context 기준 이어보기 조회
- 쿼리
  - `scope=mine|all`
  - `account_id`
  - `contact_id`
  - `context_thread_id`
  - `limit`

- 주요 응답
  - `sessions`
  - `reports`
  - `carry_over`
  - `retrieval_brief`

## 5. Event API

prefix: `/api/v1/sessions/{session_id}/events`

- `GET /`
- `GET /{event_id}`
- `PATCH /{event_id}`
- `POST /{event_id}/transition`
- `POST /bulk-transition`
- `DELETE /{event_id}`

메모:

- 이벤트 코어 타입은 `topic`, `question`, `decision`, `action_item`, `risk`다.
- API 계약은 `created_at_ms`, `updated_at_ms`를 유지할 수 있지만 PG 내부 저장은 `TIMESTAMPTZ`다.

## 6. Report API

prefix: `/api/v1/reports`

- `GET /`
- `GET /{session_id}`
- `GET /{session_id}/latest`
- `GET /{session_id}/final-status`
- `GET /{session_id}/{report_id}`
- `POST /{session_id}/markdown`
- `POST /{session_id}/pdf`
- `POST /{session_id}/regenerate`
- `GET /shared-with-me`
- `GET /shared-with-me/{report_id}`
- `GET /{session_id}/{report_id}/shares`
- `POST /{session_id}/{report_id}/shares`

메모:

- 리포트 공유는 유지한다.
- 별도 audit API는 없다.

## 7. Retrieval API

prefix: `/api/v1/retrieval`

### `GET /search`

- 목적: `pgvector + FTS` hybrid retrieval 검색
- 쿼리
  - `q`
  - `account_id`
  - `contact_id`
  - `context_thread_id`
  - `limit`

## 8. Runtime / Health API

### `GET /api/v1/runtime/readiness`

- 목적: 세션 시작 전 readiness 확인

### `GET /api/v1/runtime/monitor`

- 목적: 운영 모니터 요약 지표 조회

### `GET /api/v1/health`

- 목적: 기본 health check

## 9. WebSocket API

### `WS /api/v1/ws/audio/{session_id}`

- 목적: PCM 오디오 입력 스트림
- 쿼리
  - `input_source=mic|system_audio|mic_and_audio|file`

응답 payload 주요 필드:

- `session_id`
- `input_source`
- `utterances`
- `events`
- `error`

### `WS /api/v1/ws/text/{session_id}`

- 목적: 텍스트 입력 테스트용 WebSocket

## 운영 메모

1. live 경로와 post-meeting 경로를 분리한다.
2. 세션 종료 후 리포트 생성은 job 상태를 통해 추적한다.
3. 세션 입력 정본은 `primary_input_source`와 `actual_active_sources`다.
4. history는 carry-over와 retrieval brief를 같이 제공한다.

## 관련 문서

- [구조](구조.md)
- [DB 문서](db.md)
- [pgvector 설계](pgvector_설계.md)
