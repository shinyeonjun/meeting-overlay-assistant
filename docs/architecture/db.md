# DB 구조

이 문서는 CAPS의 현재 DB 확정안을 정리한 문서다.

핵심 원칙은 아래와 같다.

1. 정본 데이터는 `PostgreSQL`에 둔다.
2. retrieval / memory는 `PostgreSQL + pgvector` 계층으로 붙인다.
3. `SQLite`는 테스트 격리와 레거시 마이그레이션 호환용으로만 남긴다.
4. DrawSQL 시각화는 실행 스키마와 별도 파일로 관리한다.

## 관련 파일

- 실행 정본 스키마: [000_runtime_compatible_schema.sql](/D:/caps/server/app/infrastructure/persistence/postgresql/000_runtime_compatible_schema.sql)
- pgvector 추가 스키마: [010_pgvector_knowledge.sql](/D:/caps/server/app/infrastructure/persistence/postgresql/010_pgvector_knowledge.sql)
- 전체 실행 스키마: [020_runtime_with_pgvector_schema.sql](/D:/caps/server/app/infrastructure/persistence/postgresql/020_runtime_with_pgvector_schema.sql)
- DrawSQL 현재 구조 스키마: [030_drawsql_schema.sql](/D:/caps/server/app/infrastructure/persistence/postgresql/drawsql/030_drawsql_schema.sql)
- DrawSQL 목표 구조 스키마: [031_drawsql_target_schema.sql](/D:/caps/server/app/infrastructure/persistence/postgresql/drawsql/031_drawsql_target_schema.sql)
- pgvector 설계: [pgvector_설계.md](/D:/caps/docs/architecture/pgvector_설계.md)
- PG / Redis / Vector 통합 설계: [pg_redis_vector_설계.md](/D:/caps/docs/architecture/pg_redis_vector_설계.md)

## 운영 기준

### 개발
- 기본 정본 DB: `PostgreSQL`
- backend: `PERSISTENCE_BACKEND=postgresql`
- DSN: `POSTGRESQL_DSN=...`

### 테스트
- 기본 DB: `SQLite`
- 이유: 테스트 격리, 빠른 초기화, 구버전 스키마 호환 검증

### 파일 저장
DB에는 본문 전체를 넣지 않고 파일 경로만 저장하는 항목이 있다.

- 원본 녹음 파일
- transcript
- markdown report
- pdf report
- analysis artifact

예상 경로:

```text
server/data/
  recordings/
    {session_id}.{source}.wav
  reports/
    {session_id}/
      markdown.v{n}.md
      pdf.v{n}.pdf
      artifacts/
        transcript.v{n}.md
        analysis.v{n}.json
```

## 전체 ERD

### 정본 계층

```text
workspaces
  +-- workspace_members >-- users
  +-- accounts
  |    +-- contacts
  +-- context_threads
  +-- sessions
       +-- session_participants
       +-- participant_followups
       +-- utterances
       +-- overlay_events
       +-- report_generation_jobs
       +-- reports
            +-- report_shares

users
  +-- auth_password_credentials
  +-- auth_sessions
```

### retrieval / memory 계층

```text
reports
  +-- knowledge_documents
       +-- knowledge_chunks

accounts / contacts / context_threads / sessions
  +-- filter key로 knowledge_documents와 연결
```

## 테이블 확정안

## 1. 인증

### `workspaces`
- 워크스페이스 정본

주요 컬럼:
- `id`
- `slug`
- `name`
- `status`
- `created_at`
- `updated_at`

### `users`
- 내부 사용자 정본

주요 컬럼:
- `id`
- `login_id`
- `display_name`
- `job_title`
- `department`
- `status`
- `created_at`
- `updated_at`

설명:
- 로그인 식별자는 `email`이 아니라 `login_id`다.
- 권한은 `users.role`이 아니라 `workspace_members.workspace_role`을 기준으로 본다.

### `workspace_members`
- 워크스페이스와 사용자 연결

주요 컬럼:
- `workspace_id`
- `user_id`
- `workspace_role`
- `status`
- `joined_at`
- `created_at`
- `updated_at`

### `auth_password_credentials`
- 비밀번호 해시 저장

주요 컬럼:
- `user_id`
- `password_hash`
- `password_updated_at`

### `auth_sessions`
- 로그인 세션 / 토큰 상태

주요 컬럼:
- `id`
- `user_id`
- `token_hash`
- `client_type`
- `created_at`
- `expires_at`
- `revoked_at`
- `last_seen_at`

## 2. Context

### `accounts`
- 회사 / 고객사 / 거래처 정본

주요 컬럼:
- `id`
- `workspace_id`
- `name`
- `description`
- `status`
- `created_by_user_id`
- `created_at`
- `updated_at`

### `contacts`
- 상대방 사람 정본

주요 컬럼:
- `id`
- `workspace_id`
- `account_id`
- `name`
- `email`
- `job_title`
- `department`
- `notes`
- `status`
- `created_by_user_id`
- `created_at`
- `updated_at`

설명:
- `contacts.email`은 외부 상대방 연락 정보다.
- 내부 사용자 로그인과는 별개다.

### `context_threads`
- 같은 업무 흐름 / 같은 건 / 같은 논의 축

주요 컬럼:
- `id`
- `workspace_id`
- `account_id`
- `contact_id`
- `title`
- `summary`
- `status`
- `created_by_user_id`
- `created_at`
- `updated_at`

## 3. Session

### `sessions`
- 회의 1건 정본

주요 컬럼:
- `id`
- `title`
- `mode`
- `created_by_user_id`
- `account_id`
- `contact_id`
- `context_thread_id`
- `primary_input_source`
- `actual_active_sources`
- `started_at`
- `ended_at`
- `status`

설명:
- `primary_input_source`는 대표 입력 소스다.
- `actual_active_sources`는 실제 활성 입력 소스 목록이며 `JSONB`로 저장한다.
- 더 이상 `source`, `participants_json` 같은 중복 필드는 없다.

## 4. Participation

### `session_participants`
- 회의 당시 참여자 snapshot 정본

주요 컬럼:
- `session_id`
- `participant_order`
- `participant_name`
- `normalized_participant_name`
- `participant_email`
- `participant_job_title`
- `participant_department`
- `resolution_status`
- `contact_id`
- `account_id`

설명:
- `contacts`는 현재 정본이다.
- `session_participants`는 회의 시점 snapshot이다.

### `participant_followups`
- unresolved 참여자 후속 정리 작업

주요 컬럼:
- `id`
- `session_id`
- `participant_order`
- `participant_name`
- `resolution_status`
- `followup_status`
- `matched_contact_count`
- `contact_id`
- `account_id`
- `created_at`
- `updated_at`
- `resolved_at`
- `resolved_by_user_id`

설명:
- 참여자 자동 매칭이 애매하거나 실패했을 때 운영적으로 정리하는 용도다.

## 5. 발화 / 인사이트

### `utterances`
- STT 발화 원문 정본

주요 컬럼:
- `id`
- `session_id`
- `seq_num`
- `start_ms`
- `end_ms`
- `text`
- `confidence`
- `input_source`
- `stt_backend`
- `latency_ms`

설명:
- `start_ms`, `end_ms`는 세션 기준 상대 시간이다.
- 실시간 인사이트 추출의 입력 기록이자 이벤트 근거 anchor 역할을 한다.

### `overlay_events`
- 회의 중 구조화된 인사이트 정본

지원 타입:
- `topic`
- `question`
- `decision`
- `action_item`
- `risk`

주요 컬럼:
- `id`
- `session_id`
- `source_utterance_id`
- `event_type`
- `title`
- `normalized_title`
- `body`
- `evidence_text`
- `speaker_label`
- `state`
- `input_source`
- `insight_scope`
- `created_at`
- `updated_at`

설명:
- PostgreSQL 정본에서는 절대 시간을 `TIMESTAMPTZ`로 저장한다.
- 앱 내부 도메인과 일부 API 계약은 호환을 위해 epoch ms 표현을 유지할 수 있다.
- `priority`, `assignee`, `due_date`, `topic_group`, `source_screen_id` 같은 레거시 필드는 제거했다.

## 6. Report

### `reports`
- 생성된 리포트 메타데이터 정본

주요 컬럼:
- `id`
- `session_id`
- `report_type`
- `version`
- `file_path`
- `insight_source`
- `generated_by_user_id`
- `generated_at`

설명:
- markdown 본문 snapshot은 DB에서 제거했다.
- 파일 경로 기준으로 정본을 본다.

### `report_generation_jobs`
- 세션 종료 후 리포트 생성 상태

주요 컬럼:
- `id`
- `session_id`
- `status`
- `recording_path`
- `transcript_path`
- `markdown_report_id`
- `pdf_report_id`
- `error_message`
- `requested_by_user_id`
- `created_at`
- `started_at`
- `completed_at`

최소 상태:
- `pending`
- `processing`
- `completed`
- `failed`

### `report_shares`
- 리포트 공유 정본

주요 컬럼:
- `id`
- `report_id`
- `shared_by_user_id`
- `shared_with_user_id`
- `permission`
- `note`
- `created_at`

설명:
- 사용자 식별 기반 공유를 계속 가져가므로 유지한다.
- `report_audit_logs`는 제거했다.

## 7. Retrieval / pgvector

### `knowledge_documents`
- 검색 가능한 문서 메타데이터

주요 컬럼:
- `id`
- `workspace_id`
- `source_type`
- `source_id`
- `session_id`
- `report_id`
- `account_id`
- `contact_id`
- `context_thread_id`
- `title`
- `body`
- `content_hash`
- `search_tsv`
- `created_at`
- `updated_at`
- `indexed_at`

설명:
- 1차 source는 사실상 `report` 중심이다.
- `search_text`는 제거했고 `title + body` 기준으로 `search_tsv`를 만든다.
- `source_id`는 polymorphic source를 위해 `TEXT`다.

### `knowledge_chunks`
- vector 검색 최소 단위

주요 컬럼:
- `id`
- `document_id`
- `chunk_index`
- `chunk_heading`
- `chunk_text`
- `embedding_model`
- `token_count`
- `char_count`
- `embedding`
- `created_at`

설명:
- 기본 embedding 차원은 `VECTOR(768)` 기준이다.
- 현재 로컬 기본 모델은 `nomic-embed-text:latest`다.

## 핵심 인덱스

정본 계층:
- `sessions(account_id, started_at)`
- `sessions(contact_id, started_at)`
- `sessions(context_thread_id, started_at)`
- `session_participants(account_id, normalized_participant_name)`
- `session_participants(resolution_status, session_id)`
- `participant_followups(followup_status, created_at)`
- `overlay_events(session_id, event_type, state)`
- `overlay_events(session_id, created_at)`
- `reports(session_id, generated_at)`
- `report_generation_jobs(status, created_at)`

retrieval 계층:
- `GIN(search_tsv)`
- `HNSW(embedding vector_cosine_ops)`
- `knowledge_documents(workspace_id, source_type, source_id)`
- `knowledge_documents(account_id, updated_at)`
- `knowledge_documents(contact_id, updated_at)`
- `knowledge_documents(context_thread_id, updated_at)`

## retrieval 전략

1. `workspace` 필터
2. `account / contact / context_thread` 필터
3. PostgreSQL FTS로 후보 압축
4. pgvector cosine similarity로 재정렬
5. 상위 chunk 반환

즉:
- `PostgreSQL`은 정본
- `pgvector`는 회상 / 검색 계층

## 최종 정리

현재 기준으로 코어 테이블은 아래와 같다.

- `workspaces`
- `users`
- `workspace_members`
- `auth_password_credentials`
- `auth_sessions`
- `accounts`
- `contacts`
- `context_threads`
- `sessions`
- `session_participants`
- `participant_followups`
- `utterances`
- `overlay_events`
- `reports`
- `report_generation_jobs`
- `report_shares`
- `knowledge_documents`
- `knowledge_chunks`

이 목록이 현재 CAPS의 최종 DB 확정안이다.
