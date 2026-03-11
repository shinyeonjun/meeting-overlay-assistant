# internal 문서 안내

이 디렉터리는 개발 진행 과정에서 필요한 내부 메모, 계획, 설정 참고 자료를 담는다.

중요:
- 이 문서들은 현재 코드 동작의 단일 기준이 아니다.
- 구현 기준은 `architecture/`, 제품 기준은 `product/`를 우선한다.
- internal 문서는 “왜 이렇게 진행했는가”, “다음에 뭘 해야 하는가”, “개발 중 어떤 판단을 했는가”를 남기는 용도다.

## 문서 성격

### 현재도 참고 가치가 있는 문서

- [계획.md](계획.md)
- [MVP_개발백로그.md](MVP_개발백로그.md)
- [env_split_guide.md](env_split_guide.md)

### 기록성 문서

- [스프린트1_작업계획.md](스프린트1_작업계획.md)
- [tmp_settings_refs.txt](tmp_settings_refs.txt)

## 사용 원칙

- 구현을 바꾸면 internal 문서도 현재 판단 기준에 맞게 요약을 갱신한다.
- 오래된 계획은 삭제하기보다 “현재는 폐기됨”을 표시한다.
- product/architecture 문서와 충돌하면 internal 문서가 아니라 product/architecture 문서를 우선한다.
