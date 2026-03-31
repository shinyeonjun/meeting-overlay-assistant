# client/shared

`client/shared/`는 overlay와 web이 공용으로 쓰는 프론트엔드 기반 모듈 공간입니다.

현재 포함 범위:

- `src/runtime/`: API base URL 저장소 factory
- `src/auth/`: auth session 저장소 factory
- `src/api/`: 공용 HTTP / health helper

원칙:

- 앱별 UX와 상태는 각 앱에 둡니다.
- API base URL, auth session 저장소, HTTP helper처럼 중복되는 기반 코드만 shared로 올립니다.
- 루트 [`shared/`](../../shared/)는 서버-클라이언트 계약과 스키마 저장소이고, `client/shared/`는 브라우저/Tauri 실행 코드를 위한 공간입니다.
