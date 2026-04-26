# 클라이언트 구조

`client/`는 현재 제품의 공식 클라이언트 경로입니다.
이제 클라이언트는 `overlay`와 `web` 두 축으로 나뉩니다.

## 디렉터리

- [client/overlay](overlay/): Tauri 기반 회의 중 HUD
- [client/web](web/): 회의 후 중심 workspace / history / reports / assistant
- [client/shared](shared/): 공용 API 계약, auth, normalizer를 둘 자리

## 역할 분리

### `client/overlay`

- 빠른 세션 생성
- 세션 시작/종료
- 라이브 자막
- 연결 상태와 핵심 이벤트 요약
- 시스템 오디오 캡처, 항상 위 창, 클릭스루 같은 네이티브 기능

### `client/web`

- 회의 히스토리 탐색
- 회의록 생성 상태 확인과 검수
- retrieval 기반 검색
- 사후 정리용 assistant UI
- 세션 상세와 후속 조치 작업

### `client/shared`

- API 클라이언트
- payload normalizer
- 프론트 공용 타입/계약
- 공용 포맷터

## 실행 방법

### Overlay

```powershell
.\scripts\dev-client.ps1
```

### Web

```powershell
.\scripts\dev-client.ps1 -Target web
```

## 원칙

1. 회의 중 즉시성이 필요한 기능은 `overlay`에 둡니다.
2. 회의 후 정리와 긴 문맥 작업은 `web`에 둡니다.
3. 공용 계약과 API 호출 로직은 `client/shared`로 모읍니다.
4. `legacy/frontend/`는 레거시 참조용이며 신규 작업 기준이 아닙니다.
