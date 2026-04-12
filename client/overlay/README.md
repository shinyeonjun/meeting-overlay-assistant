# client/overlay

이 디렉터리는 현재 프로젝트에서 **실제 클라이언트 구현의 기준 경로**다.

여기 있는 Tauri/Vite 앱이 다음 책임을 맡는다.

- 회의 중 오버레이 UI
- 로컬 오디오 캡처
- live caption 렌더링
- live 질문 인사이트 표시
- 세션 시작/종료
- 서버 업로드 진입점

## 실행 기준

개발 중 기본 실행 경로:

```powershell
cd D:\caps\client\overlay
npm run overlay:tauri:dev
```

빌드:

```powershell
cd D:\caps\client\overlay
npm run overlay:build
```

## 레거시 경로와의 관계

- [frontend](../../frontend/) 는 호환용 진입점과 참조본으로 남아 있다.
- 실제 기능 변경은 `client/overlay/` 기준으로만 진행한다.
- 구조 개편이 완전히 끝나기 전까지는 두 경로를 병행 유지한다.
