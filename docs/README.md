# 문서 허브

이 저장소의 문서는 아래 성격으로 나뉩니다.

- `architecture/`: 현재 코드/DB/API 기준 문서
- `product/`: 사용자 흐름, 기능, 운영 정책
- `internal/`: 현재 진행 중인 메모와 작업 참고
- `research/`: 조사, 벤치마크, 비교 자료
- `archive/`: 지금은 기준 문서가 아닌 과거 기록

문서를 읽을 때는 먼저 **현재 기준 문서인지**, 아니면 **과거 기록인지**를 구분해서 보는 게 중요합니다.

## 먼저 읽기

### 최근 개발 진행과 문제 해결 흐름을 보려면

1. [개발 진행 문제 해결 기록](개발_진행_문제_해결_기록.md)

### 프로젝트 현재 구조를 이해하려면

1. [루트 README](../README.md)
2. [구조 승격 이행](architecture/구조_승격_이행.md)
3. [구조](architecture/구조.md)
4. [디렉토리 맵](architecture/디렉토리_맵.md)
5. [API](architecture/api.md)
6. [DB](architecture/db.md)

### 제품 흐름과 UX를 보려면

1. [product 안내](product/README.md)
2. [요구사항 / 기능 명세](product/요구사항_기능명세.md)
3. [사용자 플로우 / IA](product/사용자_플로우_IA.md)
4. [오버레이 UI/UX 명세](product/오버레이_UIUX명세.md)
5. [이벤트 정책 / 상태전이](product/이벤트정책_상태전이.md)
6. [운영정책 / 비기능](product/운영정책_비기능.md)

### 운영과 스크립트를 보려면

1. [루트 scripts 가이드](../scripts/README.md)
2. [server/scripts 가이드](../server/scripts/README.md)
3. [ASCII 가이드](ascii.md)

## 폴더별 설명

### `architecture/`

현재 코드 기준의 구조, API, DB, 디렉토리, PG / pgvector 방향을 설명하는 문서입니다.

### `product/`

사용자 흐름, 화면 책임, 제품 기능, 운영 정책을 설명하는 문서입니다.

### `internal/`

지금도 참고 가치가 있는 진행 메모와 내부 가이드입니다.  
공식 기준 문서가 아니므로, 구조/제품 기준은 항상 `architecture/`, `product/`를 우선합니다.

### `research/`

모델 조사, STT 실험, 벤치마크 자료입니다.  
현재 제품 결정의 배경을 이해할 때 참고하고, 구현 기준은 아닙니다.

### `archive/`

지금은 직접 참조하지 않는 과거 계획, 초반 백로그, 이전 조사 메모를 보관합니다.  
삭제하기엔 아깝지만 현재 기준으로 보기엔 혼란을 줄 수 있는 문서를 이쪽으로 보냅니다.

## 문서 업데이트 원칙

1. 현재 공식 구조는 `server / client / shared / deploy` 기준으로 쓴다.
2. `backend / frontend`는 과거 참조 경로로만 언급한다.
3. 구조 변경은 `architecture/`를 먼저 고친다.
4. 사용자 흐름 변경은 `product/`를 먼저 고친다.
5. 진행 메모는 `internal/`, 오래된 기록은 `archive/`로 보낸다.

## 같이 보면 좋은 문서

- [문서 스타일 가이드](STYLE_GUIDE.md)
- [GitHub 작업 플레이북](GITHUB_PLAYBOOK.md)
- [README 템플릿](templates/README_TEMPLATE.md)
- [상세 문서 템플릿](templates/DOC_TEMPLATE.md)
