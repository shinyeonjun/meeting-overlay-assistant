# pgvector 설계

이 문서는 CAPS 프로젝트에서 `PostgreSQL + pgvector`를 어떻게 붙일지 1차 구현 직전 수준으로 정리한 설계안이다.

기본 전제는 단순하다.

- 정본은 `PostgreSQL`이다.
- `pgvector`는 정본을 대체하지 않는다.
- `pgvector`는 `retrieval / memory / 다음 회의 브리프`를 위한 검색 계층이다.
- 1차는 과하지 않게 `report 중심 + 로컬 Ollama embedding`으로 시작한다.

## 현재 상태

지금까지 끝난 축은 아래와 같다.

- 인증
- STT / runtime
- session
- participation
- context
- events
- history
- report
- post-meeting pipeline
- PostgreSQL 1차 전환

현재 개발 기본 DB는 PostgreSQL이고, 테스트는 격리된 SQLite를 사용한다.

즉 지금은 `정본 DB를 PostgreSQL로 안정화`한 상태이고, 다음 단계가 `pgvector`다.

## pgvector를 붙이는 이유

이 프로젝트에서 pgvector는 아래 문제를 풀기 위해 필요하다.

1. 같은 `account / contact / context_thread` 안에서 과거 회의를 의미 기반으로 다시 찾기
2. 이전 리포트와 carry-over에서 지금 질문과 가까운 논의를 다시 찾기
3. 다음 회의 전에 볼 만한 요약 브리프를 최신순이 아니라 관련순으로 만들기

즉 `pgvector`는 검색과 회상을 위한 계층이다.

## 1차 범위

1차는 아래만 한다.

1. `report markdown`을 문서화한다.
2. 문서를 chunk로 나눈다.
3. chunk embedding을 저장한다.
4. `workspace / account / contact / context_thread` 필터 + `FTS + vector` hybrid retrieval을 붙인다.

1차에서 하지 않는 것:

- 발화 전체를 전부 embedding
- 별도 Vector SaaS
- multi-embedding model
- Redis와 강결합된 retrieval cache
- memory graph

## 1차 데이터 소스

스키마는 여러 source를 받을 수 있게 열어두되, 실제 1차 적재는 `report`만 한다.

허용 `source_type`:

- `report`
- `history_carry_over`
- `session_summary`

실제 1차 적재 대상:

- `report`

즉 설계는 넓게, 구현은 좁게 간다.

## 테이블 설계

### `knowledge_documents`

문서 메타데이터와 FTS 검색 기준 본문을 저장한다.

```sql
CREATE TABLE knowledge_documents (
    id TEXT PRIMARY KEY,
    workspace_id TEXT NOT NULL,
    source_type TEXT NOT NULL,
    source_id TEXT NOT NULL,
    session_id TEXT,
    report_id TEXT,
    account_id TEXT,
    contact_id TEXT,
    context_thread_id TEXT,
    title TEXT NOT NULL,
    body TEXT NOT NULL,
    content_hash TEXT NOT NULL,
    search_tsv TSVECTOR GENERATED ALWAYS AS (
        to_tsvector(
            'simple',
            concat_ws(' ', coalesce(title, ''), coalesce(body, ''))
        )
    ) STORED,
    created_at TIMESTAMPTZ NOT NULL,
    updated_at TIMESTAMPTZ NOT NULL,
    indexed_at TIMESTAMPTZ,
    UNIQUE (source_type, source_id)
);
```

설계 포인트:

- `source_type + source_id`를 natural upsert key로 쓴다.
- `report`가 다시 생성되면 새 row를 늘리지 않고 같은 document를 갱신한다.
- `content_hash`로 본문 변화가 없으면 재-embedding을 생략할 수 있다.
- `account_id / contact_id / context_thread_id`는 retrieval 필터를 위해 둔다.
- 별도 `search_text` 중간 컬럼은 두지 않고 `title + body`에서 바로 `search_tsv`를 만든다.

### `knowledge_chunks`

vector 검색의 최소 단위다.

```sql
CREATE TABLE knowledge_chunks (
    id TEXT PRIMARY KEY,
    document_id TEXT NOT NULL,
    chunk_index INTEGER NOT NULL,
    chunk_heading TEXT,
    chunk_text TEXT NOT NULL,
    embedding_model TEXT NOT NULL,
    token_count INTEGER NOT NULL DEFAULT 0,
    char_count INTEGER NOT NULL DEFAULT 0,
    embedding VECTOR(768),
    created_at TIMESTAMPTZ NOT NULL,
    UNIQUE (document_id, chunk_index)
);
```

설계 포인트:

- 1차는 embedding model 1종 고정이다.
- 로컬 기본 model은 `nomic-embed-text:latest`다.
- 차원은 `768`로 시작한다.
- `chunk_heading`은 retrieval 결과를 UI에 붙일 때 맥락을 더 빨리 보여주기 좋다.
- `token_count`, `char_count`는 chunk 품질 튜닝 지표로 쓴다.

## 인덱스 설계

### 문서 인덱스

```sql
CREATE INDEX idx_knowledge_documents_workspace_source
    ON knowledge_documents(workspace_id, source_type, source_id);

CREATE INDEX idx_knowledge_documents_account_created
    ON knowledge_documents(account_id, updated_at DESC);

CREATE INDEX idx_knowledge_documents_contact_created
    ON knowledge_documents(contact_id, updated_at DESC);

CREATE INDEX idx_knowledge_documents_thread_created
    ON knowledge_documents(context_thread_id, updated_at DESC);

CREATE INDEX idx_knowledge_documents_report_id
    ON knowledge_documents(report_id);

CREATE INDEX gin_knowledge_documents_search_tsv
    ON knowledge_documents USING GIN (search_tsv);
```

### chunk 인덱스

```sql
CREATE INDEX idx_knowledge_chunks_document
    ON knowledge_chunks(document_id, chunk_index);

CREATE INDEX hnsw_knowledge_chunks_embedding
    ON knowledge_chunks USING hnsw (embedding vector_cosine_ops);
```

기본은 `HNSW`를 우선으로 본다.

이유:

- 학습 단계 없이 바로 생성 가능하다.
- 1차 규모에서 `IVFFlat`보다 운영 감각이 단순하다.
- 데이터가 점진적으로 쌓이는 현재 구조와 잘 맞는다.

단, 실제 `pgvector` 버전 제약이나 운영 환경 이슈가 있으면 `IVFFlat`로 대체 가능하다.

## chunking 규칙

1차는 과하게 복잡하게 하지 않는다.

기본 규칙:

- markdown heading 우선 분리
- bullet list는 가급적 한 chunk 안에 유지
- 목표 크기: `800 ~ 1200자`
- overlap: `120 ~ 200자`
- 너무 짧은 chunk는 앞뒤와 병합

이유:

- 한국어 문서는 heading/bullet 구조 보존이 검색 품질에 꽤 중요하다.
- token 기반만 고집하면 구현 복잡도가 먼저 올라간다.
- 1차는 안정적인 chunk 품질이 더 중요하다.

## embedding 전략

1차 원칙:

- embedding model 1종 고정
- 문서 전체 embedding은 만들지 않음
- chunk embedding만 저장

embedding 생성 시점:

```text
report_generation_job completed
-> report markdown 확정
-> knowledge_document upsert
-> chunk 분리
-> embedding 생성
-> knowledge_chunks upsert
```

즉 `report`가 1차 knowledge 정본 입력이다.

## retrieval 전략

기본 전략은 `hybrid retrieval`이다.

1. `workspace_id` 필수 필터
2. 필요 시 `account_id / contact_id / context_thread_id` 필터
3. `FTS`로 lexical candidate 압축
4. `pgvector cosine similarity`로 semantic rerank
5. 상위 chunk를 문서 단위로 다시 묶어 응답

즉:

- FTS = 빠른 1차 후보 추리기
- pgvector = 의미 기반 재정렬

## 쿼리 예시

### account 기준 semantic retrieval

```sql
SELECT
    kc.id,
    kc.document_id,
    kc.chunk_text,
    kc.embedding <=> %(query_embedding)s AS distance
FROM knowledge_chunks kc
JOIN knowledge_documents kd ON kd.id = kc.document_id
WHERE kd.workspace_id = %(workspace_id)s
  AND kd.account_id = %(account_id)s
ORDER BY kc.embedding <=> %(query_embedding)s
LIMIT 10;
```

### FTS + vector hybrid retrieval

```sql
WITH lexical_candidates AS MATERIALIZED (
    SELECT id
    FROM knowledge_documents
    WHERE workspace_id = %(workspace_id)s
      AND search_tsv @@ plainto_tsquery('simple', %(query)s)
    ORDER BY updated_at DESC
    LIMIT 100
)
SELECT
    kc.id,
    kc.document_id,
    kc.chunk_text,
    kc.embedding <=> %(query_embedding)s AS distance
FROM knowledge_chunks kc
JOIN lexical_candidates lc ON lc.id = kc.document_id
ORDER BY kc.embedding <=> %(query_embedding)s
LIMIT 10;
```

## API 초안

### `GET /api/v1/retrieval/search`

query params:

- `q`
- `account_id`
- `contact_id`
- `context_thread_id`
- `limit`

응답:

- `documents`
- `chunks`
- `distance`
- `source_type`
- `source_id`

### `GET /api/v1/retrieval/brief`

입력:

- `account_id` 또는 `context_thread_id`

출력:

- 다음 회의 전에 읽을 만한 관련 리포트 요약
- 관련 chunk 목록
- 최근 질문 / 결정 / 액션 / 리스크 후보

## 구현 순서

1. PostgreSQL에 `vector` extension 추가
2. `knowledge_documents`, `knowledge_chunks` migration 추가
3. report 완료 후 knowledge upsert 서비스 추가
4. chunker 추가
5. embedding 생성 서비스 추가
6. retrieval query service / API 추가
7. history / brief에서 retrieval 사용

## 지금 당장 안 하는 것

- live STT 발화 단위 memory
- report 외 source 실적재
- Redis retrieval cache
- document graph / chunk graph
- rerank model 분리

## 최종 판단

이 프로젝트에서 `pgvector`는 **history와 다음 회의 브리프를 똑똑하게 만드는 retrieval 계층**으로 들어가는 게 맞다.

1차는 딱 아래만 하면 된다.

- `report -> knowledge_documents`
- `knowledge_documents -> knowledge_chunks`
- `FTS + pgvector hybrid retrieval`
- `account / contact / thread` 필터
## 현재 구현 메모

지금 기준 구현은 아래까지 진행되어 있다.

- PostgreSQL 컨테이너는 `pgvector/pgvector:pg16` 이미지로 운영
- 로컬 embedding 모델은 `nomic-embed-text:latest`
- 실제 embedding 차원은 `768`
- `010_pgvector_knowledge.sql` 기준으로 `knowledge_documents`, `knowledge_chunks` 생성
- report generation job 완료 후 새 markdown 리포트는 자동 knowledge indexing
- `manage_postgresql.py backfill-report-knowledge`로 기존 markdown 리포트 일괄 백필 가능
- `manage_postgresql.py search-retrieval`로 CLI 검색 스모크 가능
