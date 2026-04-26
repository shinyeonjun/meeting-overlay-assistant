# PostgreSQL Persistence

이 디렉터리는 CAPS의 PostgreSQL 정본 스키마와 PostgreSQL 전용 저장소 구현을 관리한다.

## 포함 파일

- `000_runtime_compatible_schema.sql`
  - 현재 런타임 계약을 최대한 그대로 유지하는 1차 호환 스키마
- `001_initial_schema.sql`
  - 장기 구조 개편을 위한 초기 설계 초안
- `010_pgvector_knowledge.sql`
  - `pgvector` 기반 retrieval 계층 스키마
- `020_runtime_with_pgvector_schema.sql`
  - `000 + 010`을 합친 현재 기준 전체 스키마
- `021_runtime_typed_target_schema.sql`
  - 현재 테이블 이름을 유지하면서 타입만 PostgreSQL 친화적으로 정리한 2차 목표 정본
- `022_runtime_typed_inplace_migration.sql`
  - 현재 runtime DB를 실제로 `021` 수준 타입 구조로 옮기기 위한 in-place migration
- `drawsql/030_drawsql_schema.sql`
  - DrawSQL import용 현재 구조 반영 스키마
- `drawsql/031_drawsql_target_schema.sql`
  - DrawSQL import용 목표 구조 스키마
- `database.py`
  - `psycopg` 연결과 트랜잭션 래퍼
- `repositories/`
  - PostgreSQL 저장소 구현

## 현재 기준과 목표 기준

### 현재 런타임 기준

- 현재 앱과 바로 맞물리는 기준은 `020_runtime_with_pgvector_schema.sql`이다.
- 현재 실제 개발 DB와는 구조적으로 동일하다.
- 차이는 일부 테이블의 물리적인 컬럼 순서뿐이며, 컬럼 이름/타입/제약조건/인덱스 기준으로는 맞는다.

### 2차 타입 개선 기준

- `021_runtime_typed_target_schema.sql`은 2차 목표 스키마다.
- 현재 런타임 테이블 이름과 핵심 컬럼 계약은 유지한다.
- 대신 아래를 정리한다.
  - 문자열 ID -> `UUID`
  - 문자열 시간 -> `TIMESTAMPTZ`
  - 범주형 문자열 -> `VARCHAR(n)`
  - 유지가 자연스러운 긴 본문/경로/메모 -> `TEXT`
  - 구조형 데이터 -> `JSONB`, `TSVECTOR`, `VECTOR`
- 이 파일은 fresh schema 기준안이다.
- 현재 운영 DB에 바로 덮어쓰는 migration 스크립트로 보면 안 된다.

### 실제 덮어쓰기 기준

- `022_runtime_typed_inplace_migration.sql`은 현재 `020` 기반 운영 DB에 실제로 적용하는 migration이다.
- 기존 테이블을 shadow table로 재적재한 뒤 교체한다.
- legacy prefix ID를 deterministic UUID로 바꾸고, 문자열 시간 컬럼을 `TIMESTAMPTZ`로 변환한다.
- 단, DB migration만으로 끝나지 않는다.
  - 앱의 ID 생성 규칙
  - 기본 workspace ID 상수
  - `str` 기반 도메인/응답 계약
  - UUID / datetime read compatibility
  를 같이 점검해야 한다.

## 현재 핵심 타입 정리

- 사용자 식별은 `login_id`
- 권한은 `workspace_members.workspace_role`
- 세션 입력 정보는 `primary_input_source`, `actual_active_sources`
- `actual_active_sources`는 `JSONB`
- `overlay_events.created_at / updated_at`는 `TIMESTAMPTZ`
- retrieval 계층은 `knowledge_documents`, `knowledge_chunks`

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

### 3. 현재 기준 전체 스키마 적용

```powershell
D:\caps\venv\Scripts\python.exe server\scripts\admin\manage_postgresql.py apply-schema --schema full --dsn "postgresql://USER:PASSWORD@HOST:5432/DBNAME"
```

### 4. 2차 타입 개선 목표 스키마 적용

```powershell
D:\caps\venv\Scripts\python.exe server\scripts\admin\manage_postgresql.py apply-schema --schema typed-target --dsn "postgresql://USER:PASSWORD@HOST:5432/DBNAME"
```

### 5. 현재 DB를 실제로 타입 migration

```powershell
D:\caps\venv\Scripts\python.exe server\scripts\admin\manage_postgresql.py apply-schema --schema typed-migration --dsn "postgresql://USER:PASSWORD@HOST:5432/DBNAME"
```

### 6. smoke check

```powershell
D:\caps\venv\Scripts\python.exe server\scripts\admin\manage_postgresql.py smoke-check --dsn "postgresql://USER:PASSWORD@HOST:5432/DBNAME"
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
- [PG / Redis / Vector 경계](/D:/caps/docs/architecture/pg_redis_vector_경계.md)
