# PostgreSQL Persistence

이 디렉터리는 CAPS의 PostgreSQL 정본 스키마와 PostgreSQL 전용 저장소 구현을 관리한다.

## 포함 파일

- `000_runtime_compatible_schema.sql`
  - 현재 런타임과 최대한 맞춘 PostgreSQL 정본 스키마
- `001_initial_schema.sql`
  - 장기 구조 참고용 초안
- `010_pgvector_knowledge.sql`
  - `pgvector` 기반 retrieval 계층 스키마
- `020_runtime_with_pgvector_schema.sql`
  - `000 + 010` 합본
- `drawsql/030_drawsql_schema.sql`
  - DrawSQL import용 현실 반영 스키마
- `drawsql/031_drawsql_target_schema.sql`
  - DrawSQL import용 목표 구조 스키마
- `database.py`
  - `psycopg` 연결/트랜잭션 헬퍼
- `repositories/`
  - PostgreSQL 저장소 구현

## 현재 기준 핵심

- 사용자 식별자는 `login_id`
- 권한은 `workspace_members.workspace_role`
- 세션 입력 정본은 `primary_input_source`, `actual_active_sources`
- `actual_active_sources`는 `JSONB`
- `overlay_events` 내부 시간은 `TIMESTAMPTZ`
- retrieval은 `knowledge_documents`, `knowledge_chunks`

## 환경 변수

```env
PERSISTENCE_BACKEND=postgresql
POSTGRESQL_DSN=postgresql://USER:PASSWORD@HOST:5432/DBNAME
```

## 적용 순서

### 1. runtime 스키마만 적용

```powershell
D:\caps\venv\Scripts\python.exe server\scripts\admin\manage_postgresql.py apply-schema --schema runtime --dsn "postgresql://USER:PASSWORD@HOST:5432/DBNAME"
```

### 2. pgvector만 추가 적용

```powershell
D:\caps\venv\Scripts\python.exe server\scripts\admin\manage_postgresql.py apply-schema --schema pgvector --dsn "postgresql://USER:PASSWORD@HOST:5432/DBNAME"
```

### 3. 전체 스키마 한 번에 적용

```powershell
D:\caps\venv\Scripts\python.exe server\scripts\admin\manage_postgresql.py apply-schema --schema full --dsn "postgresql://USER:PASSWORD@HOST:5432/DBNAME"
```

### 4. SQLite 데이터 이행

```powershell
D:\caps\venv\Scripts\python.exe server\scripts\admin\manage_postgresql.py migrate-sqlite --dsn "postgresql://USER:PASSWORD@HOST:5432/DBNAME" --truncate-target
```

### 5. smoke check

```powershell
D:\caps\venv\Scripts\python.exe server\scripts\admin\manage_postgresql.py smoke-check --dsn "postgresql://USER:PASSWORD@HOST:5432/DBNAME" --sqlite-path server\data\meeting_overlay.db
```

## pgvector 운영 메모

기존 리포트를 retrieval 계층으로 백필하려면:

```powershell
D:\caps\venv\Scripts\python.exe server\scripts\admin\manage_postgresql.py backfill-report-knowledge --dsn "postgresql://caps:caps@127.0.0.1:55432/caps"
```

CLI로 retrieval 결과를 바로 확인하려면:

```powershell
D:\caps\venv\Scripts\python.exe server\scripts\admin\manage_postgresql.py search-retrieval --dsn "postgresql://caps:caps@127.0.0.1:55432/caps" --query "리포트" --limit 5
```

## 참고 문서

- [DB 문서](/D:/caps/docs/architecture/db.md)
- [PostgreSQL 전환 계획](/D:/caps/docs/architecture/postgresql_전환_계획.md)
- [PG / Redis / Vector 설계](/D:/caps/docs/architecture/pg_redis_vector_설계.md)
