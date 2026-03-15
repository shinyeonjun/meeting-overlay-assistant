# CAPS

[![Status](https://img.shields.io/badge/status-postgres%20%2B%20pgvector-informational)](docs/architecture/db.md)
[![Server](https://img.shields.io/badge/server-FastAPI-009688)](https://fastapi.tiangolo.com/)
[![Client](https://img.shields.io/badge/client-Tauri%20%2B%20Vite-4F46E5)](https://tauri.app/)
[![Runtime](https://img.shields.io/badge/runtime-onprem_client--server-334155)](docs/architecture/구조.md)

CAPS는 온프렘 회의 보조 제품을 목표로 하는 프로젝트입니다.  
실시간 STT와 인사이트 추출, 회의 종료 후 리포트 생성, 히스토리 탐색, retrieval 기반 다음 회의 브리프까지 하나의 흐름으로 다룹니다.

현재 공식 기준 경로는 `server / client / shared / deploy`입니다.  
`backend / frontend`는 과거 MVP 참조본으로만 남아 있습니다.

## 현재 공식 구조

- `server/`: FastAPI 서버, 비즈니스 로직, PostgreSQL / pgvector persistence
- `client/`: Tauri + Vite 기반 overlay 클라이언트
- `shared/`: API 계약, enum, schema
- `deploy/`: 로컬/운영 배포 스크립트와 compose
- `docs/`: 아키텍처, 제품, 운영 문서

실제 서버 진입점은 `server.app.main:app`이고, 실제 클라이언트 진입점은 `client/overlay`입니다.

## 현재 제품 축

- 실시간 STT와 live caption
- `question / decision / action_item / risk / topic` 이벤트 추출
- 세션 종료 후 전체 오디오 기반 transcript / markdown / pdf 리포트 생성
- `Account / Contact / ContextThread` 기반 회의 맥락 관리
- 히스토리 조회와 retrieval brief
- 사용자 식별 기반 리포트 공유
- 서버 운영 콘솔 (`dashboard / doctor / logs / settings / profiles`)

제거된 축:

- `screen_contexts`와 OCR 기반 화면 컨텍스트
- `report_audit_logs`
- `users.email`, `users.role`, `sessions.source`
- `reports.snapshot_markdown`, `knowledge_documents.search_text`

## 빠른 시작

### 1. 서버 의존성 설치

```powershell
python -m venv venv
.\venv\Scripts\activate
pip install -r requirements-app.txt
```

### 2. PostgreSQL 컨테이너 실행

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\dev-postgres.ps1 up
```

### 3. 서버 실행

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\dev-server.ps1
```

### 4. 클라이언트 실행

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\dev-client.ps1
```

### 5. 서버와 클라이언트 동시 실행

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\dev-stack.ps1
```

### 6. 서버 운영 콘솔 실행

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\server-admin.ps1 dashboard
```

## 개발 기준

- 개발 기본 DB: `PostgreSQL`
- retrieval / memory: `PostgreSQL + pgvector`
- 테스트 기본 DB: `SQLite` 격리 인스턴스
- 로그인 식별자: `login_id`
- 권한 기준: `workspace_members.workspace_role`
- 세션 입력 정본: `primary_input_source`, `actual_active_sources`

## 운영 / 개발 진입점

- 개발 스택: [scripts/README.md](scripts/README.md)
- 서버 스크립트: [server/scripts/README.md](server/scripts/README.md)
- 문서 허브: [docs/README.md](docs/README.md)

## 문서 읽는 순서

1. [구조 승격 이행](docs/architecture/구조_승격_이행.md)
2. [구조](docs/architecture/구조.md)
3. [디렉토리 맵](docs/architecture/디렉토리_맵.md)
4. [API](docs/architecture/api.md)
5. [DB](docs/architecture/db.md)
6. [ASCII 가이드](docs/ascii.md)

## 현재 상태 요약

- 서버는 PostgreSQL 기준으로 동작합니다.
- pgvector 기반 retrieval과 history brief가 연결돼 있습니다.
- 리포트는 전체 오디오 기반 후처리 파이프라인으로 생성합니다.
- 클라이언트는 Tauri overlay 기준으로 session / history / report / share 흐름이 붙어 있습니다.
- SQLite는 운영 정본이 아니라 테스트 격리와 레거시 마이그레이션 호환용입니다.

## 참고

- 전체 구조: [docs/architecture/구조.md](docs/architecture/구조.md)
- DB 설계: [docs/architecture/db.md](docs/architecture/db.md)
- PG / pgvector: [docs/architecture/pg_redis_vector_설계.md](docs/architecture/pg_redis_vector_설계.md)
- 제품 흐름: [docs/product/사용자_플로우_IA.md](docs/product/사용자_플로우_IA.md)
