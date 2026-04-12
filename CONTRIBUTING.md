# Contributing Guide

이 저장소는 현재 `server / client / shared / deploy` 구조로 승격 중이다.

기여하거나 문서를 수정할 때는 아래 원칙을 먼저 따른다.

## 기본 원칙

1. 공식 기준 경로는 `server/`, `client/`, `shared/`, `deploy/` 다.
2. `backend/`, `frontend/` 는 레거시 참조본으로 유지한다.
3. 구조 승격 중에는 작은 단위로, step by step 으로 수정한다.
4. 깨진 파일은 부분 수정보다 전체 재작성을 우선한다.
5. 문서는 코드와 같은 날 업데이트하는 것을 원칙으로 한다.

## 문서 수정 규칙

문서를 수정할 때는 아래 문서를 먼저 본다.

- [문서 인덱스](docs/README.md)
- [문서 스타일 가이드](docs/STYLE_GUIDE.md)
- [GitHub 작업 플레이북](docs/GITHUB_PLAYBOOK.md)

문서 역할은 다음처럼 분리한다.

- `README.md`: 프로젝트 입구 문서
- `docs/architecture/`: 구조와 기술 경계
- `docs/product/`: 정책과 UX
- `docs/internal/`: 계획과 메모
- `docs/research/`: 실험과 근거 자료

## 코드 변경 시 같이 봐야 할 문서

- API 변경: `docs/architecture/api.md`
- 저장 구조 변경: `docs/architecture/db.md`
- 클라이언트 UX 변경: `docs/product/오버레이_UIUX명세.md`
- 이벤트 정책 변경: `docs/product/이벤트정책_상태전이.md`

## PR 작성 규칙

PR 은 아래를 짧고 명확하게 적는 것이 좋다.

1. 무엇을 바꿨는가
2. 왜 바꿨는가
3. 어떤 위험이 있는가
4. 무엇으로 검증했는가

가능하면 스크린샷, 실행 명령, 영향 범위를 함께 남긴다.

## 커밋 / 브랜치 감각

이 저장소는 과한 설명보다 의미가 바로 드러나는 이름을 선호한다.

예:

- 브랜치: `feature/onprem-client-server`
- 커밋: `docs: align architecture docs with server-client structure`

## 마지막 체크리스트

- 공식 경로와 레거시 경로를 섞어 쓰지 않았는가
- 문서 역할이 맞는 위치에 있는가
- 관련 문서 링크를 같이 갱신했는가
- README 에 너무 상세한 내부 메모를 밀어넣지 않았는가
