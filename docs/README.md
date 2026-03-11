# 문서 인덱스

이 디렉터리는 `Meeting Overlay Assistant`의 현재 구현, 운영 정책, 실험 근거를 정리한 문서 모음이다.  
문서는 `현재 코드 기준`으로 유지하는 것을 원칙으로 하며, 구현과 충돌하는 계획성 메모는 `internal`, 실험성 메모는 `research`에 분리한다.

## 문서 읽는 순서

처음 프로젝트를 이해할 때는 아래 순서대로 보는 것을 권장한다.

1. [루트 README](../README.md)
2. [아키텍처 개요](architecture/구조.md)
3. [API 문서](architecture/api.md)
4. [UI/UX 명세](product/오버레이_UIUX명세.md)
5. [기능 명세](product/요구사항_기능명세.md)
6. [이벤트 정책](product/이벤트정책_상태전이.md)
7. [운영 정책](product/운영정책_비기능.md)

## 디렉터리별 역할

### `architecture/`

실제 구현 구조를 설명한다.

- [구조](architecture/구조.md): 시스템 전체 흐름과 모듈 경계
- [설계](architecture/설계.md): 주요 설계 판단과 트레이드오프
- [API 문서](architecture/api.md): 현재 노출된 HTTP/WebSocket API
- [DB](architecture/db.md): SQLite 스키마와 저장 원칙
- [디렉토리 맵](architecture/디렉토리_맵.md): 코드베이스 탐색용 파일 단위 안내

### `product/`

사용자 관점 동작, 정책, UI, 이벤트 처리 규칙을 설명한다.

- [요구사항 / 기능 명세](product/요구사항_기능명세.md)
- [오버레이 UI/UX 명세](product/오버레이_UIUX명세.md)
- [운영정책 / 비기능](product/운영정책_비기능.md)
- [이벤트정책 / 상태전이](product/이벤트정책_상태전이.md)

### `research/`

로컬 STT, 하이브리드 전략, 모델 선택, 벤치마크 등 **설계 근거**를 담는다.  
이 문서들은 구현 의사결정의 배경 자료이며, 단일 진실 원천은 아니다. 현재 코드와 다를 수 있으므로 구현 확인은 `architecture/`, 정책 확인은 `product/`를 우선한다.

### `internal/`

백로그, 계획, 개발 메모, 설정 참고 자료를 둔다.  
팀 내부 운영 문서 성격이며, 사용자 공개 문서나 최종 산출물 기준 문서로 쓰지 않는다.

## 현재 문서화 원칙

- 실시간 경로와 최종 리포트 경로를 분리해서 설명한다.
- `세션 종료 = 리포트 자동 생성`으로 쓰지 않는다. 현재는 수동 생성 정책이다.
- 실시간 인사이트는 질문만 노출하는 현재 정책을 기준으로 쓴다.
- 리포트 산출물은 세션별 폴더와 `artifacts/` 구조를 기준으로 설명한다.
- 연구 문서는 측정값, JSON 산출물, 실험 파일 경로를 가능한 한 함께 남긴다.

## 유지보수 가이드

- API가 바뀌면 `architecture/api.md`를 먼저 수정한다.
- 저장 구조가 바뀌면 `architecture/db.md`, `product/운영정책_비기능.md`를 같이 수정한다.
- UI가 바뀌면 `product/오버레이_UIUX명세.md`를 같이 수정한다.
- STT 전략이나 모델 선택이 바뀌면 `research/` 문서도 같이 갱신한다.
