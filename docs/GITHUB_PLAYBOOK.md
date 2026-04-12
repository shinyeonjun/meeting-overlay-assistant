# GitHub 작업 플레이북

이 문서는 이 저장소를 GitHub 에서 보기 좋은 개발자 저장소처럼 운영하기 위한 실무 규칙을 정리한다.

핵심은 화려함이 아니라 일관성이다.

## 1. README 는 입구 문서처럼 쓴다

좋은 README 는 아래를 빠르게 알려준다.

1. 이 프로젝트가 무엇인가
2. 어디서 실행하는가
3. 현재 공식 기준 경로가 무엇인가
4. 자세한 문서는 어디 있는가

README 에 넣지 않는 것이 좋은 것:

- 장문의 작업 일지
- 내부 TODO
- 실험 로그
- 설계 세부 판단 전부

이런 내용은 `docs/` 로 보낸다.

## 2. 문서는 역할별로 쪼갠다

- `README.md`: 입구
- `docs/README.md`: 문서 포털
- `docs/architecture/`: 구조와 기술 경계
- `docs/product/`: 정책과 기대 동작
- `docs/internal/`: 계획과 메모
- `docs/research/`: 실험 근거

GitHub 에서 문서가 잘 읽히는 저장소는 이 경계가 명확하다.

## 3. 제목만 봐도 문서 정체가 보여야 한다

좋은 제목:

- `구조 승격 이행 가이드`
- `오버레이 UI/UX 명세`
- `DB 구조`

약한 제목:

- `정리`
- `메모`
- `생각`
- `임시`

## 4. PR 은 짧고 명확하게 쓴다

좋은 PR 설명은 아래 네 줄이면 충분한 경우가 많다.

- 변경 내용
- 변경 이유
- 영향 범위
- 검증 방법

예:

```text
## Summary
- align architecture docs with server/client structure
- rewrite outdated DB and requirements docs

## Why
- root docs and detailed docs were using mixed legacy/current paths

## Validation
- manual doc link review
```

## 5. 스크린샷과 예시는 아끼지 않는다

GitHub 문서는 텍스트만으로 다 설명하려 하지 말고, 필요한 곳엔 아래를 같이 둔다.

- 실행 명령
- JSON 예시
- 디렉터리 트리
- UI 스크린샷

특히 README 와 UI/UX 문서에서 효과가 크다.

## 6. 문서도 코드처럼 리뷰한다

문서 리뷰 때는 아래를 본다.

- 현재 기준과 맞는가
- 레거시와 공식 경로를 구분했는가
- 제목과 첫 문단만 보고도 목적이 보이는가
- 다른 문서와 충돌하지 않는가
- 다음에 읽을 문서 링크가 있는가

## 7. 이 저장소에서 특히 중요한 GitHub 감각

현재는 구조 승격 브랜치이기 때문에 아래 표현을 엄격하게 구분해야 한다.

- `server/client/shared/deploy` = 현재 공식 기준
- `backend/frontend` = 레거시 참조본

이 한 줄만 지켜도 문서 품질이 훨씬 올라간다.

## 8. 추천 작업 루프

문서를 고칠 때는 아래 순서가 좋다.

1. 문서 목적을 한 줄로 적는다.
2. 현재 기준 경로를 적는다.
3. 세부 내용을 정리한다.
4. 관련 문서 링크를 붙인다.
5. 루트 README 나 docs 인덱스에 링크가 필요한지 확인한다.

이 루프를 계속 반복하면 문서가 점점 GitHub 저장소다운 느낌을 갖게 된다.
