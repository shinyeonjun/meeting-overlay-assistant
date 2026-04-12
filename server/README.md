# 서버 구조

`server/`는 현재 제품의 공식 서버 경로입니다.

현재 진입점:

- 통합 서버: `server.app.main:app`
- Control API 전용: `server.app.entrypoints.control_api:app`
- Live API 전용: `server.app.entrypoints.live_api:app`
- Report Worker: `python -m server.app.workers.report.generation_worker`

현재 내부 구조:

- `app/entrypoints/`: 배포 단위별 진입점
- `app/api/http/route_groups/`: control / live / shared 라우트 묶음
- `app/api/http/routes/`: 실제 FastAPI 라우트
- `app/services/`: 도메인 서비스
- `app/workers/`: 비동기 worker
- `app/infrastructure/artifacts/`: 로컬 artifact storage
- `app/infrastructure/persistence/postgresql/`: PostgreSQL / pgvector
- `app/infrastructure/queues/redis/`: Redis 큐 구현

실행 예시:

```powershell
.\scripts\dev-server.ps1
.\scripts\dev-server.ps1 -EntryPoint server.app.entrypoints.control_api:app
.\scripts\dev-server.ps1 -Port 8012 -EntryPoint server.app.entrypoints.live_api:app
.\scripts\dev-report-worker.ps1
```
