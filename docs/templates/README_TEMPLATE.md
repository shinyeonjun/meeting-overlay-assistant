# 프로젝트 이름

한 줄 설명. 이 프로젝트가 무엇인지, 어떤 문제를 해결하는지 먼저 적는다.

## 현재 상태

- 공식 기준 경로:
- 주요 실행 대상:
- 레거시 경로가 있다면:

## 빠른 시작

### 서버 실행

```powershell
# 예시
uvicorn server.app.main:app --host 127.0.0.1 --port 8011
```

### 클라이언트 실행

```powershell
# 예시
cd client\overlay
npm run overlay:tauri:dev
```

## 디렉터리 개요

```text
project/
  client/
  server/
  docs/
```

## 문서 읽는 순서

1. [문서 인덱스](docs/README.md)
2. [구조 문서](docs/architecture/구조.md)
3. [API 문서](docs/architecture/api.md)

## 운영 원칙

1. 현재 공식 기준 경로를 명확히 적는다.
2. 레거시 경로가 있다면 역할을 분리해서 적는다.
3. 자세한 설계 내용은 `docs/` 로 분리한다.
