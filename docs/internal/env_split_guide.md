# 환경 설정 분리 가이드

이 문서는 현재 기준의 환경 설정 책임을 정리한다.

## 원칙

1. 서버와 클라이언트 설정을 분리한다.
2. DB, Redis, STT, artifact 같은 인프라 설정은 서버가 가진다.
3. 클라이언트는 API 주소와 UI 동작 설정만 가진다.
4. 개발과 운영 모두 기본 DB는 PostgreSQL이다.

## 서버 설정

대표 항목:

- `APP_ENV`
- `DEBUG`
- `POSTGRESQL_DSN`
- `TEST_POSTGRESQL_DSN`
- `REDIS_URL`
- `SERVER_HOST`
- `SERVER_PORT`

## 클라이언트 설정

대표 항목:

클라이언트는 Vite 환경변수(`VITE_*`)를 쓴다. 각 client의 `.env.example`이 기준이다.

- overlay: `VITE_CONTROL_API_BASE_URL`(8011), `VITE_LIVE_API_BASE_URL`(8012), `VITE_WEB_WORKSPACE_URL`(1430)
- overlay 시스템 오디오: `VITE_BACKEND_PYTHON`, `VITE_LIVE_AUDIO_SCRIPT_PATH` (상대 경로는 저장소 루트 기준)
- web: `VITE_SERVER_BASE_URL`(8011)

## 개발 기본값

- 로컬 인프라: Docker 기반 `PostgreSQL + Redis`
- 테스트: `TEST_POSTGRESQL_DSN` 기준 별도 격리 DB
- retrieval: `pgvector`

## 주의사항

- `DATABASE_PATH` 같은 SQLite 기반 설정은 더 이상 active 경로가 아니다.
- artifact 저장 경로는 서버에서만 관리한다.
- 같은 `.env`를 서버와 클라이언트가 공용으로 들고 가지 않는다.
