# client/web

`client/web/`는 CAPS의 회의 후 중심 workspace 경로입니다.

주요 책임:

- 회의록 검수와 공유
- 히스토리 / retrieval / carry-over
- 회의 기반 assistant 질의
- 후속 작업 정리

현재 구조:

- `src/app/`: 앱 조립, section 전환, handoff query 해석
- `src/features/`: overview, history, reports, assistant UI
- `src/services/`: API 호출
- `src/config/`: 서버 URL 설정
- `src/styles/`: web workspace 스타일

실행:

```powershell
cd D:\caps\client\web
npm install
npm run web:dev
```
