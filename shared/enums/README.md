# Enums

`shared/enums/`는 서버와 클라이언트가 같이 써야 하는 상태값 목록을 모아두는 자리다.

지금 단계에서는 실제 공용 코드 패키지보다, 아래 두 가지를 먼저 고정하는 역할을 맡는다.

1. 사람이 읽는 기준 문서
2. 테스트가 검증할 기계 판독용 catalog

## 현재 관리 범위

- 세션 모드와 상태
- 오디오 입력 방식
- 워크스페이스 역할
- 히스토리 조회 scope
- 이벤트 타입과 상태
- 리포트 형식과 생성 상태
- 공유 권한
- live utterance kind / stability
- auth token type

## 파일 역할

- `catalog.json`
  - 테스트와 도구가 읽는 기준 catalog
- `catalog.md`
  - 사람이 빠르게 훑는 요약 문서

## 운영 원칙

- 새 상태값을 서버나 클라이언트에 추가하면 먼저 여기 catalog를 갱신한다.
- 문자열 enum은 소문자 snake_case를 기본으로 유지한다.
- 사용자 표시 문구는 catalog가 아니라 UI/문서 레이어에서 번역한다.
