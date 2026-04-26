# client/overlay

`client/overlay/`는 CAPS의 회의 중 HUD 경로입니다.

주요 책임:

- 빠른 세션 생성과 시작 / 종료
- 라이브 자막과 연결 상태 표시
- 회의 중에는 라이브 자막 중심으로 표시
- 진행 중 이벤트 보드는 `VITE_LIVE_EVENT_INSIGHTS_ENABLED=true`일 때만 쓰는 실험 기능
- web workspace로 handoff

현재 구조:

- `src/app/`: 부팅과 이벤트 바인딩
- `src/features/`: auth, session, live, events, workspace 같은 기능 표면
- `src/controllers/`: 실제 화면 제어 로직
- `src/services/`: API / Tauri 브리지
- `src/state/`: overlay 클라이언트 상태

실행:

```powershell
cd D:\caps\client\overlay
npm run overlay:tauri:dev
```

기본 런타임 주소:

- `VITE_CONTROL_API_BASE_URL`: Control API 서버 주소
- `VITE_LIVE_API_BASE_URL`: Live runtime / STT 서버 주소
- `VITE_LIVE_EVENT_INSIGHTS_ENABLED`: MVP 기본값은 `false`, 실시간 질문/이벤트 보드 실험 시에만 `true`
