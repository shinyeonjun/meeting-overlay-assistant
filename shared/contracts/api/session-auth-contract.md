# Session / Auth Contract

이 문서는 현재 클라이언트와 서버가 함께 따르는 `session` / `auth` HTTP 계약을 정리한다.

## auth

### auth config

- 경로: `GET /api/v1/auth/config`
- 목적: 클라이언트가 로그인 필요 여부와 초기 관리자 생성 필요 여부를 먼저 판단한다.
- 응답 필드
  - `enabled`
  - `bootstrap_required`
  - `user_count`

### bootstrap admin

- 경로: `POST /api/v1/auth/bootstrap-admin`
- 목적: 서버 설치 직후 첫 관리자 계정을 만든다.
- 요청 필드
  - `login_id`
  - `password`
  - `display_name`
  - `job_title`
  - `department`
  - `client_type`

### login

- 경로: `POST /api/v1/auth/login`
- 목적: 클라이언트가 bearer token을 발급받는다.
- 요청 필드
  - `login_id`
  - `password`
  - `client_type`

### auth session response

- 응답 필드
  - `access_token`
  - `token_type`
  - `expires_at`
  - `user`

### auth user response

- 응답 필드
  - `id`
  - `login_id`
  - `display_name`
  - `workspace_id`
  - `workspace_name`
  - `workspace_slug`
  - `workspace_role`
  - `workspace_status`
  - `status`
  - `created_at`
  - `updated_at`

## session

### create session draft

- 경로: `POST /api/v1/sessions`
- 목적: live를 바로 켜기 전에 draft 세션을 먼저 만든다.
- 요청 필드
  - `title`
  - `mode`
  - `primary_input_source`
  - `account_id`
  - `contact_id`
  - `context_thread_id`
  - `participants`
- 호환 메모
  - 구버전 클라이언트가 보내는 `source`는 서버에서 `primary_input_source`로 변환해 받는다.

### start session

- 경로: `POST /api/v1/sessions/{session_id}/start`
- 목적: draft 세션을 `running`으로 전이한다.

### end session

- 경로: `POST /api/v1/sessions/{session_id}/end`
- 목적: running 세션을 `ended`로 전이한다.

### session response

- 목적: 세션 라이프사이클과 최소 참여자 요약만 전달한다.
- 응답 필드
  - `id`
  - `title`
  - `mode`
  - `primary_input_source`
  - `actual_active_sources`
  - `status`
  - `started_at`
  - `ended_at`
  - `created_by_user_id`
  - `account_id`
  - `contact_id`
  - `context_thread_id`
  - `participants`
  - `participant_summary`

### participant summary

- 목적: 세션 응답을 가볍게 유지하면서도 참여자 연결 상태를 요약한다.
- 응답 필드
  - `total_count`
  - `linked_count`
  - `unmatched_count`
  - `ambiguous_count`
  - `unresolved_count`
  - `pending_followup_count`
  - `resolved_followup_count`

## participation

### get session participation

- 경로: `GET /api/v1/sessions/{session_id}/participants`
- 목적: 세션 참여자 snapshot, 후보, 요약을 상세 조회한다.
- 응답 필드
  - `session_id`
  - `participants`
  - `participant_candidates`
  - `summary`

### participant response

- 목적: 세션 참여자 snapshot 정본을 표현한다.
- 응답 필드
  - `name`
  - `normalized_name`
  - `contact_id`
  - `account_id`
  - `email`
  - `job_title`
  - `department`
  - `resolution_status`

### participant candidates

- 목적: 자동 매핑되지 않았거나 후보가 여러 개인 참여자를 후속 정리 대상으로 보여준다.
- 응답 필드
  - `name`
  - `account_id`
  - `resolution_status`
  - `matched_contact_count`
  - `matched_contacts`

### participant candidate match

- 목적: `ambiguous` 참여자에게 제시할 기존 contact 후보를 표현한다.
- 응답 필드
  - `contact_id`
  - `account_id`
  - `name`
  - `email`
  - `job_title`
  - `department`

### list participant followups

- 경로: `GET /api/v1/sessions/{session_id}/participants/followups`
- 목적: 세션 종료 후 unresolved 참여자 후속 작업 목록을 조회한다.

### create contact from participant

- 경로: `POST /api/v1/sessions/{session_id}/participants/contacts`
- 목적: `unmatched` 참여자를 새 contact로 승격하고 세션과 바로 연결한다.
- 요청 필드
  - `participant_name`
  - `account_id`
  - `email`
  - `job_title`
  - `department`
  - `notes`

### link existing contact to participant

- 경로: `POST /api/v1/sessions/{session_id}/participants/links`
- 목적: `ambiguous` 참여자를 기존 contact 하나와 연결한다.
- 요청 필드
  - `participant_name`
  - `contact_id`

## 운영 메모

- 사용자 인증 식별자는 `email`이 아니라 `login_id`다.
- 세션 입력 정본은 `primary_input_source`와 `actual_active_sources`다.
- 세션 응답의 참여자 정보는 요약용이고, 참여자 정본 조회는 participation API가 담당한다.
- enum 문자열은 `shared/enums/catalog.json` 기준으로 유지한다.
- `session`, `participation`, `auth` 필드가 바뀌면 이 문서와 schema를 같이 갱신한다.
