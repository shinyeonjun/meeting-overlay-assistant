# PostgreSQL 전환 계획

이 문서는 CAPS의 저장 계층을 `PostgreSQL + pgvector + Redis` 기준으로 정리하고, 현재 기준 스키마와 다음 단계 목표 스키마를 구분해 기록한다.

## 현재 상태

- 개발 기본 DB는 PostgreSQL이다.
- 테스트도 PostgreSQL 전용 격리 DB를 사용한다.
- 운영 보조 CLI는 `apply-schema`, `smoke-check`, `backfill-report-knowledge`, `search-retrieval`를 제공한다.
- report worker와 비동기 queue는 Redis를 기준으로 움직인다.

관련 파일:

- [000_runtime_compatible_schema.sql](/D:/caps/server/app/infrastructure/persistence/postgresql/000_runtime_compatible_schema.sql)
- [020_runtime_with_pgvector_schema.sql](/D:/caps/server/app/infrastructure/persistence/postgresql/020_runtime_with_pgvector_schema.sql)
- [021_runtime_typed_target_schema.sql](/D:/caps/server/app/infrastructure/persistence/postgresql/021_runtime_typed_target_schema.sql)
- [022_runtime_typed_inplace_migration.sql](/D:/caps/server/app/infrastructure/persistence/postgresql/022_runtime_typed_inplace_migration.sql)
- [manage_postgresql.py](/D:/caps/server/scripts/admin/manage_postgresql.py)
- [docker-compose.infrastructure.yml](/D:/caps/deploy/server/docker-compose.infrastructure.yml)

## 전환 원칙

1. 저장 계층은 PostgreSQL only로 유지한다.
2. 파일 artifact는 DB에 직접 넣지 않고 별도 artifact 경로로 관리한다.
3. retrieval은 PostgreSQL 내부의 `pgvector` 계층으로 붙인다.
4. 비동기 처리와 wake-up 신호는 Redis queue로 분리한다.
5. 현재 런타임 호환 스키마와 2차 타입 개선 정본을 분리해 관리한다.

## 현재 정본 범위

현재 런타임 기준에서 실제로 쓰는 테이블은 아래다.

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
- `session_post_processing_jobs`
- `note_correction_jobs`
- `report_generation_jobs`
- `report_shares`
- `knowledge_documents`
- `knowledge_chunks`

## 스키마 기준점

### 1. 현재 런타임 기준

- 기준 파일: [020_runtime_with_pgvector_schema.sql](/D:/caps/server/app/infrastructure/persistence/postgresql/020_runtime_with_pgvector_schema.sql)
- 의미:
  - 현재 앱 코드와 가장 직접적으로 맞물리는 기준
  - 실제 개발 DB와 구조적으로 동일한 기준
  - 일부 테이블의 컬럼 물리 순서만 다를 수 있고, 의미상 스키마는 같다

### 2. 2차 타입 개선 기준

- 기준 파일: [021_runtime_typed_target_schema.sql](/D:/caps/server/app/infrastructure/persistence/postgresql/021_runtime_typed_target_schema.sql)
- 의미:
  - 현재 테이블 이름과 핵심 컬럼 계약은 유지
  - 과도한 `TEXT` 의존을 줄이고 PostgreSQL 친화 타입으로 정리
- 아직 현재 런타임이 직접 사용하는 스키마는 아님
- fresh schema 설계 기준안이지, 기존 DB에 바로 덮는 migration 스크립트는 아님

### 3. 실제 덮어쓰기 migration 기준

- 기준 파일: [022_runtime_typed_inplace_migration.sql](/D:/caps/server/app/infrastructure/persistence/postgresql/022_runtime_typed_inplace_migration.sql)
- 의미:
  - 현재 `020` 기반 DB를 실제로 `021` 수준 타입으로 옮기는 SQL
  - shadow table 재적재 방식으로 기존 데이터를 안전하게 치환
  - prefix 기반 문자열 ID를 deterministic UUID로 변환
  - 문자열 시간 컬럼을 `TIMESTAMPTZ`로 변환

## 실제 DB 감사 결과

현재 개발 DB를 기준으로 보면, 시간 컬럼은 대부분 바로 `TIMESTAMPTZ`로 캐스팅 가능했다.
하지만 ID는 바로 `UUID`로 캐스팅 가능한 상태가 아니었다.

- `workspace-default`
- `session-...`
- `report-...`
- `post-job-...`
- `utt-...`
- `evt-...`
- `knowledge-document-...`

즉, 실제 migration은 단순 `ALTER COLUMN TYPE uuid`로는 안 되고, prefix를 벗겨 UUID로 치환하는 별도 매핑이 필요했다.

## 2차 타입 개선 핵심

`021`에서 정리한 방향은 아래와 같다.

- `id`, `*_id` -> `UUID`
- `created_at`, `updated_at`, `started_at`, `completed_at`, `lease_expires_at` -> `TIMESTAMPTZ`
- `status`, `type`, `role`, `source`, `mode` -> `VARCHAR(n)`
- `login_id`, `email` -> `CITEXT`
- `actual_active_sources` -> `JSONB`
- retrieval 검색 필드 -> `TSVECTOR`
- embedding -> `VECTOR(768)`

반대로 아래는 `TEXT` 유지가 자연스럽다.

- 긴 본문
- 메모
- 에러 메시지
- 파일 경로
- artifact 경로/키
- 증거 문장

## 현재 반영된 계약 변화

- `users.email` 대신 `login_id`를 사용한다.
- 권한은 `workspace_members.workspace_role`에서 관리한다.
- `sessions.primary_input_source`, `sessions.actual_active_sources`를 표준 입력 정보로 둔다.
- `sessions.actual_active_sources`는 `JSONB`다.
- `overlay_events.created_at / updated_at`는 `TIMESTAMPTZ`다.
- SQLite migration 경로와 SQLite 저장소 구현은 active 코드에서 제거됐다.

## 운영 메모

- raw audio, transcript, markdown, pdf는 artifact로 관리한다.
- PostgreSQL은 메타데이터와 retrieval 인덱스를 담당한다.
- Redis는 queue, lease, wake-up 용도로만 사용한다.

## 다음 단계

### 1. 앱 계약 이관

`021`을 실제 런타임 기준으로 쓰려면 앱 계층도 같이 바뀌어야 한다.

- 문자열 ID -> UUID 타입 계약 정리
- 문자열 시간 -> `datetime` 계약 정리
- repository / schema / API 응답 타입 정리
- prefix 기반 ID 생성 규칙 제거
- 기본 workspace ID 상수 재정의

### 2. Migration 전략 분리

`021`은 설계 기준안이라서, 실제 이관에는 별도 migration 계획이 필요하다.

- 기존 문자열 ID를 UUID로 바꾸는 전략
- 시간 문자열을 `TIMESTAMPTZ`로 옮기는 전략
- 데이터 백필과 롤백 기준

### 3. 후속 과제

- artifact id 기반 참조 전환 완료
- assistant worker 분리
- 배포/백업/복구 절차 구체화
