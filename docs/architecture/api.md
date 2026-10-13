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
- 메모: 세션 종료와 리포트 생성은 분리되어 있다. 종료 자체는 세션 상태만 바꾸고, 리포트 생성 job은 workspace에서 별도로 시작한다.

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

### `GET /api/v1/sessions/{session_id}`

- 목적: 세션 한 건 조회 (응답은 `POST /api/v1/sessions/`와 같다)

### `PATCH /api/v1/sessions/{session_id}`

- 목적: 세션 제목 변경
- 요청: `{"title": "..."}`

### `DELETE /api/v1/sessions/{session_id}`

- 목적: 세션과 관련 데이터 삭제. 성공하면 `204`

### `POST /api/v1/sessions/{session_id}/reprocess`

- 목적: 저장된 녹음으로 후처리(재전사, 화자 분리, 노트)를 다시 실행
- 녹음 파일이 없으면 `400`

### `GET /api/v1/sessions/{session_id}/processing`

- 목적: 후처리 상태 조회
- 주요 응답
  - `status`: `not_started`, `queued`, `processing`, `completed`, `failed`
  - `canonical_transcript_version`, `canonical_events_version`
  - `latest_job_id`, `latest_job_status`, `latest_job_error_message`

### `GET /api/v1/sessions/{session_id}/recording`

- 목적: 세션 녹음 파일(WAV) 내려받기

### `GET /api/v1/sessions/{session_id}/transcript`

- 목적: 정본 발화 목록 조회
- 항목 주요 필드
  - `speaker_label`: 화자 분리 결과 라벨 (예: `SPEAKER_00`, 분리 안 됨이면 `speaker-unknown`)
  - `speaker_name`: 화면에 보일 이름. 사용자가 붙인 이름, 없으면 `화자 1`처럼 나온 순서로 매긴 기본 이름
  - `text`, `raw_text`, `is_corrected`: 노트 보정이 있으면 `text`는 보정본, `raw_text`는 원문

### `GET /api/v1/sessions/{session_id}/speakers`

- 목적: 회의 기록의 화자 목록 조회
- 주요 응답
  - `canonical_transcript_version`
  - `max_name_length`: 이름 최대 글자 수 (40)
  - `items[]`: `speaker_label`, `display_name`, `default_name`, `custom_name`, `utterance_count`
- 기본 이름은 처음 말한 순서대로 `화자 1`, `화자 2`다. 화자 분리가 안 된 라벨은 전부 미분류일 때 `참석자`, 아니면 `미분류`다.

### `PUT /api/v1/sessions/{session_id}/speakers`

- 목적: 화자 라벨에 이름을 붙인다. 같은 라벨의 모든 발화와 이후 리포트에 반영된다.
- 요청

```json
{
  "speaker_label": "SPEAKER_00",
  "display_name": "김민수"
}
```

- `display_name`이 비어 있거나 `null`이면 기본 이름으로 되돌린다.
- 응답은 `GET /speakers`와 같다.
- 오류
  - `409`: 후처리 중이라 바꿀 수 없음
  - `404`: 이 회의 기록에 없는 화자 라벨
  - `400`: 이름이 40자를 넘음
- 이름은 정본 버전(`canonical_transcript_version`)에 묶인다. 다시 정리(`reprocess`)로 정본이 바뀌면 이전 이름은 쓰이지 않는다.

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
- `GET /{session_id}/job`
- `GET /{session_id}/{report_id}`
- `POST /{session_id}/job`
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

### `GET /health`

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
2. 세션 종료 후 리포트 생성은 workspace에서 수동으로 시작하고, 이후 job 상태를 통해 추적한다.
3. 세션 입력 정본은 `primary_input_source`와 `actual_active_sources`다.
4. history는 carry-over와 retrieval brief를 같이 제공한다.

## 관련 문서

- [구조](구조.md)
- [DB 문서](db.md)
- [pgvector 설계](pgvector_설계.md)
