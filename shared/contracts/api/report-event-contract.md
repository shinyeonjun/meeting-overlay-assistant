# Report / Event Contract

이 문서는 현재 클라이언트와 서버가 공유하는 `report`, `share`, `event` HTTP 계약을 정리한다.

## report

### report item

- 목적: 목록과 상세가 공통으로 쓰는 회의록 메타데이터
- 응답 필드
  - `id`
  - `session_id`
  - `report_type`
  - `version`
  - `file_path`
  - `insight_source`
  - `generated_by_user_id`
  - `generated_at`

### latest report

- 목적: 상세 보기와 미리보기에 쓰는 최신 회의록 응답
- 추가 필드
  - `content`

### final report status

- 목적: 세션 종료 후 회의록 생성 상태 요약
- 응답 필드
  - `session_id`
  - `status`
  - `report_count`
  - `latest_report_id`
  - `latest_report_type`
  - `latest_generated_at`
  - `latest_file_path`

## share

### create report share

- 경로: `POST /api/v1/reports/{session_id}/{report_id}/shares`
- 요청 필드
  - `shared_with_login_id`
  - `note`

### report share item

- 목적: 한 회의록의 현재 공유 상태를 보여준다.
- 응답 필드
  - `id`
  - `report_id`
  - `shared_by_*`
  - `shared_with_*`
  - `permission`
  - `note`
  - `created_at`

### shared report inbox item

- 목적: 현재 사용자가 공유받은 회의록 목록
- 응답 필드
  - `share_id`
  - `report_id`
  - `session_id`
  - `report_type`
  - `version`
  - `file_path`
  - `file_name`
  - `shared_by_*`
  - `permission`
  - `note`
  - `shared_at`

## event

### event item

- 목적: live 보드, history, carry-over가 공통으로 쓰는 이벤트 단위
- 응답 필드
  - `id`
  - `session_id`
  - `event_type`
  - `title`
  - `body`
  - `evidence_text`
  - `speaker_label`
  - `state`
  - `source_utterance_id`
  - `created_at_ms`
  - `updated_at_ms`
  - `input_source`
  - `insight_scope`

### event update request

- 목적: 사용자가 이벤트 본문과 상태를 보정한다.
- 요청 필드
  - `event_type`
  - `title`
  - `body`
  - `state`
  - `evidence_text`
  - `speaker_label`

### event transition request

- 목적: 이벤트 상태 전이 규칙을 적용한다.
- 요청 필드
  - `target_state`
  - `title`
  - `body`
  - `evidence_text`
  - `speaker_label`

### bulk transition

- 목적: 여러 이벤트를 한 번에 같은 상태로 전이한다.
- 요청 필드
  - `event_ids`
  - `target_state`

## 현재 기준 메모

- 회의록 공유의 사용자 식별자는 `email`이 아니라 `login_id`다.
- 별도 `report_audit_logs` 계약은 제거했다.
- 이벤트 코어 계약에서는 `priority`, `assignee`, `due_date`, `topic_group` 같은 예전 호환 필드를 더 이상 정본으로 보지 않는다.
- 이벤트 시간은 API에서는 `*_ms`를 유지할 수 있지만, PostgreSQL 내부는 `TIMESTAMPTZ`로 저장한다.
