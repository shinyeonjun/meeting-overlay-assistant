# PostgreSQL Persistence

이 디렉터리는 CAPS의 PostgreSQL 스키마(Alembic 마이그레이션)와 PostgreSQL 전용 저장소 구현을 관리한다.

## 포함 파일

- `migrations/`
  - Alembic 마이그레이션. `versions/0001_baseline.py`가 기준선이다.
  - 스키마 변경은 여기에 새 리비전을 추가한다. 스키마 SQL 파일을 직접 고치지 않는다.
- `020_runtime_with_pgvector_schema.sql`
  - 기준선 리비전(`0001_baseline`)이 실행하는 완전 스키마(런타임 + pgvector). 기준선 이후에는 참고용이다.
- `drawsql/030_drawsql_schema.sql`, `drawsql/031_drawsql_target_schema.sql`
  - DrawSQL import용 설계 스키마. 런타임과 연결되지 않는다.
- `database.py`
  - `psycopg_pool` 연결 풀과 트랜잭션 헬퍼. 시각 컬럼은 UTC ISO 문자열로 돌려준다.
- `repositories/`
  - PostgreSQL 저장소 구현

## 현재 기준 핵심

- 사용자 식별자는 `login_id`
- 권한은 `workspace_members.workspace_role`
- 세션 입력 정본은 `primary_input_source`, `actual_active_sources`
- `actual_active_sources`는 `JSONB`
- 시각 컬럼은 전부 `TIMESTAMPTZ`로 저장한다. 애플리케이션 경계에서는 UTC ISO 문자열이다.
- retrieval은 `knowledge_documents`, `knowledge_chunks`

## 환경 변수

```env
POSTGRESQL_DSN=postgresql://USER:PASSWORD@HOST:5432/DBNAME
```

## 마이그레이션 적용

```powershell
.\venv\Scripts\python.exe server\scripts\admin\manage_postgresql.py apply-schema --dsn "postgresql://USER:PASSWORD@HOST:5432/DBNAME"
```

최신 리비전까지 올린다. 이미 적용된 리비전은 건너뛰므로 여러 번 실행해도 안전하다.

## smoke check

```powershell
.\venv\Scripts\python.exe server\scripts\admin\manage_postgresql.py smoke-check --dsn "postgresql://USER:PASSWORD@HOST:5432/DBNAME"
```

## 새 스키마 변경 추가

```powershell
.\venv\Scripts\alembic.exe -c server\app\infrastructure\persistence\postgresql\migrations\alembic.ini revision -m "변경 내용"
```

생성된 `migrations/versions/*.py`의 `upgrade()`에 SQL을 쓴다. 이미 배포된 리비전은 고치지 않고, 변경마다 새 리비전을 만든다.

## pgvector 운영 메모

기존 리포트를 retrieval 계층으로 백필하려면:

```powershell
.\venv\Scripts\python.exe server\scripts\admin\manage_postgresql.py backfill-report-knowledge --dsn "postgresql://caps:caps@127.0.0.1:55432/caps"
```

CLI로 retrieval 결과를 바로 확인하려면:

```powershell
.\venv\Scripts\python.exe server\scripts\admin\manage_postgresql.py search-retrieval --dsn "postgresql://caps:caps@127.0.0.1:55432/caps" --query "리포트" --limit 5
```

## 참고 문서

- [DB 문서](/docs/architecture/db.md)
- [PostgreSQL 전환 계획](/docs/architecture/postgresql_전환_계획.md)
- [PG / Redis / Vector 설계](/docs/architecture/pg_redis_vector_설계.md)
