# MVP 개발 백로그

## P0

### 리포트 분석 품질

- [ ] 질문/결정/액션아이템/리스크 dedupe 2차
- [ ] 메타 문장 제거 규칙 강화
- [ ] 참고 전사 길이/개수 제한
- [ ] PDF 섹션별 문구 다듬기

### 이벤트 추출 품질

- [ ] decision / action_item 구분 정교화
- [ ] risk 과추출 감소
- [ ] evidence_text 자연스러움 개선

### STT 구조 개선

- [ ] `stability` 기반 live 렌더 보정 검증
- [ ] `fast_final` 동작 검증
- [ ] `early_eou / final_eou` 설계 확정

## P1

### 운영성

- [ ] 리포트 생성 progress 표시
- [ ] 리포트 생성 실패 이유 표시
- [ ] 고정밀 transcript 재사용 정책 검토

### 관측 지표

- [ ] `final_queue_delay_ms` 수집 정리
- [ ] `matched/standalone ratio` 시각화 기준 정리
- [ ] 리포트 생성 시간 기록

## P2

### 구조 개선

- [ ] `dependencies.py` 단순화
- [ ] `audio_pipeline_service.py` 책임 분리
- [ ] 리포트 파이프라인 단계별 서비스 분해

### 실험성 검토

- [ ] LangChain 리포트 분석 도입 재검토
- [ ] 자동 리포트 생성 정책 재검토
