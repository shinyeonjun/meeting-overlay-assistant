# PostgreSQL / Redis / Vector 통합 설계

이 문서는 CAPS에서 `PostgreSQL`, `Redis`, `pgvector`를 각각 어디에 쓰는지 정리한다.

## 현재 결론

- `PostgreSQL`이 정본이다.
- `pgvector`는 PostgreSQL 위에 붙는 retrieval 계층이다.
- `Redis`는 아직 미도입이고, 멀티 worker / queue / lock / cache가 필요해질 때 붙인다.

## 1. PostgreSQL

현재 정본 테이블:

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

현재 기준:

- 사용자 식별자는 `login_id`
- 세션 입력 정본은 `primary_input_source`, `actual_active_sources`
- `actual_active_sources`는 `JSONB`
- `overlay_events` 내부 시간은 `TIMESTAMPTZ`

실행 스키마:

- [000_runtime_compatible_schema.sql](/D:/caps/server/app/infrastructure/persistence/postgresql/000_runtime_compatible_schema.sql)
- [020_runtime_with_pgvector_schema.sql](/D:/caps/server/app/infrastructure/persistence/postgresql/020_runtime_with_pgvector_schema.sql)

## 2. pgvector

현재 CAPS는 별도 Vector DB 대신 **PostgreSQL + pgvector**로 간다.

retrieval 계층 테이블:

- `knowledge_documents`
- `knowledge_chunks`

역할:

- 과거 리포트와 회의 문맥을 semantic retrieval로 검색
- history timeline의 `retrieval_brief` 생성
- 다음 회의 brief의 기반 데이터 제공

주요 포인트:

- `knowledge_documents.source_id`는 `TEXT`
- `search_text`는 제거했고 `title + body -> search_tsv`로 정리
- 벡터 차원은 현재 `VECTOR(768)`

스키마:

- [010_pgvector_knowledge.sql](/D:/caps/server/app/infrastructure/persistence/postgresql/010_pgvector_knowledge.sql)

## 3. Redis

Redis는 설계만 열어둔 상태다. 현재 정본 경로에는 들어가지 않는다.

나중에 붙일 가능성이 높은 곳:

- `report_generation_job` queue
- distributed lock
- 짧은 TTL cache

예시 key:

- `caps:stream:report-generation-jobs`
- `caps:lock:report-job:{job_id}`
- `caps:cache:history:timeline:{scope_hash}`

원칙:

- 정본은 PostgreSQL에 둔다.
- Redis는 실행 보조로만 쓴다.

## 도입 순서

1. PostgreSQL 정본 안정화
2. pgvector retrieval 정착
3. Redis 도입 여부 판단

## 한 줄 정리

> CAPS는 현재 `PostgreSQL 정본 + pgvector retrieval` 구조이고, Redis는 나중에 worker/queue/cache 필요가 생길 때 붙인다.
