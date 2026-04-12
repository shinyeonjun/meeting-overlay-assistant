# PostgreSQL 전환 계획

이 문서는 CAPS의 SQLite 중심 구조를 PostgreSQL 중심 구조로 옮긴 뒤, 현재 어떤 상태인지 정리한다.

## 현재 상태

- 개발 기본 DB는 PostgreSQL이다.
- 테스트는 SQLite 격리 인스턴스를 계속 쓴다.
- `apply-schema`, `migrate-sqlite`, `smoke-check` 운영 스크립트가 있다.
- `full` 스키마 적용과 smoke check를 실제로 검증했다.

관련 파일:

- [000_runtime_compatible_schema.sql](/D:/caps/server/app/infrastructure/persistence/postgresql/000_runtime_compatible_schema.sql)
- [020_runtime_with_pgvector_schema.sql](/D:/caps/server/app/infrastructure/persistence/postgresql/020_runtime_with_pgvector_schema.sql)
- [manage_postgresql.py](/D:/caps/server/scripts/admin/manage_postgresql.py)

## 전환 원칙

1. 첫 전환은 runtime-compatible하게 간다.
2. 정본 이름을 한 번에 예쁘게 바꾸지 않는다.
3. 파일 artifact는 계속 파일 스토리지에 둔다.
4. retrieval과 queue는 정본 전환과 분리한다.

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

## 현재 기준 변경점

- `users.email` 대신 `login_id`
- `users.role` 제거, 권한은 `workspace_members.workspace_role`
- `sessions.source` 제거, `primary_input_source`를 정본으로 사용
- `sessions.actual_active_sources`는 `JSONB`
- `overlay_events.created_at / updated_at`는 PostgreSQL 내부에서 `TIMESTAMPTZ`
- `report_audit_logs`, `screen_contexts`, `snapshot_markdown`, `search_text` 제거

## 운영 메모

- raw audio, transcript, markdown, pdf는 파일 artifact로 관리한다.
- PostgreSQL에는 메타데이터와 정본 관계만 저장한다.
- `pgvector`는 PostgreSQL 위에 붙는 retrieval 계층으로 관리한다.
- Redis는 아직 정본 경로에 넣지 않는다.

## 남은 과제

- retrieval 품질 튜닝
- 공유 UX 정리
- 오디오 보관 정책 정리
- 배포/백업/복구 정책 구체화
