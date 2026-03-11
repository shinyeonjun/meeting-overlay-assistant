# DB 구조

현재 저장소는 SQLite를 사용한다.  
주 저장 대상은 다음 네 가지다.

- 세션
- 발화
- 이벤트
- 리포트 메타데이터

실제 산출물 파일은 DB가 아니라 파일 시스템에 저장한다.

## 1. 저장 원칙

### DB에 저장하는 것

- 세션 메타데이터
- live / final 발화 메타데이터
- 이벤트 상태와 근거 문장
- 리포트 메타데이터
- snapshot markdown

### 파일로 저장하는 것

- markdown / pdf 리포트 본문
- transcript artifact
- analysis JSON artifact
- 세션 녹음 파일

즉 SQLite는 `메타데이터와 조회용 인덱스`, 파일 시스템은 `대형 산출물` 역할을 맡는다.

## 2. 테이블 개요

### `sessions`

세션 기본 정보와 활성 입력 소스를 저장한다.

주요 컬럼:
- `id`
- `title`
- `mode`
- `source`
- `primary_input_source`
- `actual_active_sources`
- `started_at`
- `ended_at`
- `status`

의미:
- 세션 생성/종료 상태
- 어떤 입력 소스를 실제로 사용했는지
- overview와 UI 표시 기준

### `utterances`

세션 중 생성된 발화를 저장한다.

주요 컬럼:
- `id`
- `session_id`
- `seq_num`
- `start_ms`
- `end_ms`
- `text`
- `confidence`
- `input_source`
- `stt_backend`
- `latency_ms`

의미:
- live partial/final을 포함한 발화 이력
- 소스별 발화 분석
- transcript 재구성

인덱스:
- `uq_utterances_session_seq`
- `idx_utterances_session_seq`

### `screen_contexts`

화면 OCR/컨텍스트를 저장한다.

주요 컬럼:
- `id`
- `session_id`
- `captured_at_ms`
- `ocr_text`
- `title_hint`
- `keywords_json`
- `image_path`

현재는 핵심 경로보다 보조 경로에 가깝다.

### `overlay_events`

질문, 결정 사항, 액션 아이템, 리스크 같은 이벤트를 저장한다.

주요 컬럼:
- `id`
- `session_id`
- `source_utterance_id`
- `source_screen_id`
- `event_type`
- `title`
- `normalized_title`
- `body`
- `evidence_text`
- `speaker_label`
- `state`
- `priority`
- `assignee`
- `due_date`
- `topic_group`
- `input_source`
- `insight_scope`
- `created_at_ms`
- `updated_at_ms`

의미:
- `event_type`: question / decision / action_item / risk
- `state`: 내부 상태 전이용 값
- `evidence_text`: 리포트 및 검토용 근거 문장
- `insight_scope`: live / report 등 생성 범위 구분

인덱스:
- `idx_overlay_events_session_type`
- `idx_overlay_events_session_created`
- `idx_overlay_events_source_utterance`

### `reports`

리포트 메타데이터와 snapshot markdown을 저장한다.

주요 컬럼:
- `id`
- `session_id`
- `report_type`
- `version`
- `file_path`
- `insight_source`
- `snapshot_markdown`
- `generated_at`

의미:
- `report_type`: markdown / pdf
- `version`: 재생성 버전
- `file_path`: 실제 산출물 경로
- `insight_source`: `high_precision_audio` 또는 `live_fallback`
- `snapshot_markdown`: 생성 시점의 markdown 본문 스냅샷

인덱스:
- `idx_reports_session_generated`

## 3. 파일 저장 구조와 DB 관계

리포트는 아래 구조로 저장한다.

```text
backend/data/reports/{session_id}/
  markdown.v1.md
  pdf.v1.pdf
  artifacts/
    markdown.v1.transcript.md
    markdown.v1.analysis.json
    pdf.v1.transcript.md
    pdf.v1.analysis.json
```

DB에는 이 중:
- `reports.file_path`
- `reports.snapshot_markdown`
같은 메타 정보만 저장한다.

세션 녹음 파일은:

```text
backend/data/recordings/
```

아래에 임시로 저장하며, Git 추적 대상이 아니다.

## 4. 현재 데이터 정책

### 리포트

- 자동 생성하지 않는다.
- 사용자가 수동으로 Markdown 또는 PDF를 생성한다.
- 세션 녹음이 있으면 고정밀 STT 경로를 우선 사용한다.

### 이벤트

- UI에서는 상태명을 거의 숨기지만, DB에서는 상태를 유지한다.
- 리포트 반영 규칙과 lifecycle 검증에 필요하기 때문이다.

### 발화

- live 경로와 final 경로를 모두 남길 수 있다.
- 현재는 실시간 자막과 리포트 품질을 분리하기 위해 발화 데이터가 중요하다.

## 5. 스키마 변경 시 같이 봐야 할 곳

- `backend/app/infrastructure/persistence/sqlite/schema.py`
- `backend/app/infrastructure/persistence/sqlite/database.py`
- `backend/app/infrastructure/persistence/sqlite/repositories/`
- `docs/architecture/api.md`
- `docs/product/운영정책_비기능.md`
