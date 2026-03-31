# PostgreSQL 전환 계획

이 문서는 CAPS의 영속성 계층을 `PostgreSQL + pgvector + Redis` 기준으로 정리한 현재 상태를 기록한다.

## 현재 상태

- 개발 기본 DB는 PostgreSQL이다.
- 테스트도 PostgreSQL 전용 격리 DB를 사용한다.
- 운영 보조 CLI는 `apply-schema`, `smoke-check`, `backfill-report-knowledge`, `search-retrieval`만 유지한다.
- report worker와 비동기 queue는 Redis를 기준으로 움직인다.

관련 파일:

- [000_runtime_compatible_schema.sql](/D:/caps/server/app/infrastructure/persistence/postgresql/000_runtime_compatible_schema.sql)
- [020_runtime_with_pgvector_schema.sql](/D:/caps/server/app/infrastructure/persistence/postgresql/020_runtime_with_pgvector_schema.sql)
- [manage_postgresql.py](/D:/caps/server/scripts/admin/manage_postgresql.py)
- [docker-compose.infrastructure.yml](/D:/caps/deploy/server/docker-compose.infrastructure.yml)

## 전환 원칙

1. 런타임 경로는 PostgreSQL only로 유지한다.
2. 파일 artifact는 DB에 직접 넣지 않고 별도 artifact 경로로 관리한다.
3. retrieval은 PostgreSQL 내부의 pgvector 계층으로 붙인다.
4. 비동기 처리와 wake-up 신호는 Redis queue로 분리한다.

## 현재 정본 범위

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

## 핵심 변경점

- `users.email` 대신 `login_id`를 사용한다.
- 권한은 `workspace_members.workspace_role`에서 관리한다.
- `sessions.primary_input_source`, `sessions.actual_active_sources`를 정본으로 쓴다.
- `sessions.actual_active_sources`는 `JSONB`로 저장한다.
- `overlay_events.created_at / updated_at`는 `TIMESTAMPTZ`다.
- SQLite migration 경로와 SQLite 저장소 구현은 active 코드에서 제거했다.

## 운영 메모

- raw audio, transcript, markdown, pdf는 artifact로 관리한다.
- PostgreSQL은 메타데이터와 retrieval 정본을 담당한다.
- Redis는 queue, lease, wake-up 용도로만 사용한다.

## 남은 과제

- artifact id 기반 참조 전환 완료
- assistant worker 분리
- 배포/백업/복구 절차 구체화
