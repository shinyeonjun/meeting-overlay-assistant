# 환경 설정 분리 가이드

## 1. 목적

구조 정리 이후에는 로컬 MVP 시절의 단일 `.env` 감각에서 벗어나, 서버와 클라이언트의 책임에 맞게 환경 설정을 분리해야 합니다.  
특히 현재는 개발 기본 DB가 `PostgreSQL`이고, retrieval도 `pgvector`를 기준으로 동작하므로 예전 SQLite 중심 예시는 더 이상 현재 기준이 아닙니다.

이 문서는 어떤 설정을 어디에 두는지 정리합니다.

## 2. 기본 원칙

1. 서버 설정과 클라이언트 설정을 분리한다.
2. DB, STT 모델, 저장소 경로 같은 정본 책임은 서버가 가진다.
3. 클라이언트는 API 주소와 UI 동작 관련 설정만 가진다.
4. 개발용 예시와 운영용 예시를 섞지 않는다.

## 3. 서버 설정

서버는 아래 항목을 가집니다.

- `APP_ENV`
- `DEBUG`
- `PERSISTENCE_BACKEND`
- `POSTGRESQL_DSN`
- `SERVER_STORAGE_DIR`
- `STT_MODEL_PATH`
- `SERVER_HOST`
- `SERVER_PORT`

### 현재 개발 기준 예시

```env
APP_ENV=development
DEBUG=true
PERSISTENCE_BACKEND=postgresql
POSTGRESQL_DSN=postgresql://caps:caps@127.0.0.1:55432/caps
STT_MODEL_PATH=server/models/stt/faster-whisper-large-v3-turbo-ct2
SERVER_STORAGE_DIR=server/data
SERVER_HOST=127.0.0.1
SERVER_PORT=8011
```

### 보조 설정

`DATABASE_PATH`는 테스트 격리나 레거시 마이그레이션 호환용으로만 남을 수 있습니다.  
운영/개발 기본 정본은 `PostgreSQL`입니다.

## 4. 클라이언트 설정

클라이언트는 아래 항목만 가집니다.

- `CLIENT_API_BASE_URL`
- `CLIENT_DEFAULT_SOURCE`
- `CLIENT_ENABLE_DEV_TEXT`
- `CLIENT_LOG_LEVEL`

### 현재 개발 기준 예시

```env
CLIENT_API_BASE_URL=http://127.0.0.1:8011
CLIENT_DEFAULT_SOURCE=system_audio
CLIENT_ENABLE_DEV_TEXT=false
CLIENT_LOG_LEVEL=info
```

클라이언트는 DB 경로, STT 모델 경로, artifact 저장 경로를 알 필요가 없습니다.

## 5. 프로필 / JSON 설정

프로필 JSON은 행동 정책과 런타임 옵션만 가집니다.

예:

- 입력 소스 기본값
- 이벤트 추출 정책
- retrieval 검색 옵션
- 리포트 생성 옵션

넣지 말아야 할 것:

- 절대 파일 경로
- DB 접속 정보
- 서버 저장소 경로
- 테스트 fixture 경로

즉 `.env`는 배치 환경, JSON은 동작 정책으로 나눕니다.

## 6. STT 모델 경로 정책

STT 모델은 항상 서버 기준 경로로 잡습니다.

- `STT_MODEL_PATH`는 명시적인 로컬 모델 디렉토리를 가리킨다.
- startup 로그에서 실제 로드 경로를 확인한다.
- Hugging Face cache 경로에 기대는 fallback은 보조 수단일 뿐, 주 기준이 아니다.

정상 로그 예:

```text
source=D:\caps\server\models\stt\faster-whisper-large-v3-turbo-ct2
```

## 7. 개발 / 운영 분리

### 개발

- 로컬 PostgreSQL 컨테이너
- 로컬 artifact 저장소 (`server/data`)
- 테스트는 SQLite 격리

### 운영

- 관리되는 PostgreSQL
- private 네트워크
- 별도 artifact 저장 정책
- 백업 / 복구 / 롤백 정책

같은 `.env`를 개발과 운영에 그대로 복사하는 방식은 지양합니다.

## 8. 권장 파일 분리

장기적으로는 아래처럼 나누는 게 맞습니다.

- `server/.env`
- `client/overlay/.env`
- `deploy/server/server.env.example`
- `deploy/client/client.env.example`

현재 repo 루트 `.env`는 전환기 편의용이므로, 장기적으로는 책임 단위별 파일로 나누는 게 맞습니다.

## 9. 요약

- 서버는 `PostgreSQL`과 STT, artifact 저장소를 관리한다.
- 클라이언트는 API 주소와 UI 옵션만 가진다.
- 프로필 JSON은 동작 정책만 가진다.
- SQLite는 정본이 아니라 테스트/호환용이다.
- 현재 개발 기준 예시는 `PERSISTENCE_BACKEND=postgresql`과 `POSTGRESQL_DSN`이다.
