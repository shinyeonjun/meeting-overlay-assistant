# client/web

`client/web/`는 CAPS의 회의 후 중심 workspace 경로입니다.

주요 책임:

- 회의 기록(정본 발화) 확인과 화자 이름 붙이기
- 리포트 생성·검수
- 히스토리 / retrieval / carry-over
- 회의 기반 assistant 질의 (현재는 retrieval 검색 결과 표시)
- 후속 작업 정리

현재 구조:

- `src/app/`: 앱 조립, section 전환, handoff query 해석
- `src/features/`: workspace(회의 기록·화자 이름), overview, reports, assistant UI
- `src/services/`: API 호출
- `src/config/`: 서버 URL 설정
- `src/styles/`: web workspace 스타일

실행:

```powershell
cd client\web
npm install
npm run web:dev
```

개발 서버는 `http://127.0.0.1:1430`에서 뜹니다. 서버의 기본 CORS 허용 목록(`CORS_ALLOWED_ORIGINS`)에 1430 포트가 들어 있습니다. 다른 포트로 띄우면 이 값에 주소를 더해야 API 호출이 됩니다.

빌드와 테스트:

```powershell
npm run web:build
npm test
```

`npm test`는 `tests/*.test.js`를 `node --test`로 실행합니다. 아직 CI에는 들어 있지 않습니다.
