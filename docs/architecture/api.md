# API 문서

이 문서는 현재 코드 기준의 HTTP / WebSocket 인터페이스를 정리한다.  
기본 prefix는 `/api/v1`이다.

## 1. 세션 API

### `POST /api/v1/sessions`

새 세션을 생성한다.

요청 예시:

```json
{
  "title": "주간 회의",
  "mode": "meeting",
  "source": "system_audio"
}
```

응답 필드:

- `id`
- `title`
- `mode`
- `source`
- `status`
- `started_at`
- `ended_at`
- `primary_input_source`
- `actual_active_sources`

비고:
- 세션 생성은 스트리밍 준비 단계이며, 리포트를 생성하지 않는다.

### `POST /api/v1/sessions/{session_id}/end`

세션을 종료한다.

중요:
- 현재는 **리포트를 자동 생성하지 않는다.**
- 종료 후 사용자가 리포트를 수동 생성한다.

### `GET /api/v1/sessions/{session_id}/overview`

세션 overview를 조회한다.

응답에 포함되는 주요 항목:

- 세션 기본 정보
- `current_topic`
- `questions`
- `decisions`
- `action_items`
- `risks`
- `metrics`

metrics 예:
- `recent_average_latency_ms`
- `recent_utterance_count_by_source`
- `insight_metrics`

## 2. 이벤트 API

prefix: `/api/v1/sessions/{session_id}/events`

### `GET /api/v1/sessions/{session_id}/events`

세션 이벤트 목록을 조회한다.

쿼리:
- `event_type`
- `state`

응답 필드:
- `id`
- `session_id`
- `event_type`
- `title`
- `body`
- `evidence_text`
- `speaker_label`
- `state`
- `priority`
- `assignee`
- `due_date`
- `topic_group`
- `source_utterance_id`
- `source_screen_id`
- `created_at_ms`
- `updated_at_ms`
- `input_source`
- `insight_scope`

### `GET /api/v1/sessions/{session_id}/events/{event_id}`

이벤트 단건 조회.

### `PATCH /api/v1/sessions/{session_id}/events/{event_id}`

이벤트를 수동 수정한다.

현재 프론트는 이 API를 통해 주로 제목 수정에 사용한다.

### `POST /api/v1/sessions/{session_id}/events/{event_id}/transition`

검증된 상태 전이를 수행한다.

예:
- question: `open -> answered`
- action_item: `open -> confirmed`
- risk: `active -> resolved`

### `POST /api/v1/sessions/{session_id}/events/bulk-transition`

여러 이벤트를 한 번에 전이한다.

참고:
- 현재 프론트의 기본 UX에서는 bulk 액션을 단순화해 사용하지 않지만, API 자체는 유지한다.

### `DELETE /api/v1/sessions/{session_id}/events/{event_id}`

이벤트 삭제.

참고:
- 현재 기본 UI에선 삭제 액션을 메인 플로우에 노출하지 않는다.

## 3. 리포트 API

prefix: `/api/v1/reports`

### `POST /api/v1/reports/{session_id}/markdown`

Markdown 리포트를 수동 생성한다.

동작:
- 세션 녹음 파일이 있으면 자동 참조
- 고정밀 STT 기반 분석 수행
- 세션 폴더에 markdown와 artifact 생성

선택 쿼리:
- `audio_path`

응답에 포함되는 항목:
- `id`
- `session_id`
- `report_type`
- `version`
- `file_path`
- `insight_source`
- `content`
- `transcript_path`
- `analysis_path`
- `speaker_transcript`
- `speaker_events`

### `POST /api/v1/reports/{session_id}/pdf`

PDF 리포트를 수동 생성한다.

응답 항목:
- `id`
- `session_id`
- `report_type`
- `version`
- `file_path`
- `insight_source`
- `source_markdown`
- `transcript_path`
- `analysis_path`

### `POST /api/v1/reports/{session_id}/regenerate`

같은 세션의 새 버전 markdown/pdf를 다시 생성한다.

용도:
- 이벤트 수정 후 새 버전 리포트 생성

### `GET /api/v1/reports/{session_id}`

세션의 리포트 목록 조회.

### `GET /api/v1/reports/{session_id}/latest`

최신 리포트 조회.

리포트가 없으면 `404`.

### `GET /api/v1/reports/{session_id}/final-status`

리포트 생성 상태 조회.

주요 응답 필드:
- `status`
- `report_count`
- `latest_report_id`
- `latest_report_type`
- `latest_generated_at`
- `latest_file_path`

### `GET /api/v1/reports/{session_id}/{report_id}`

리포트 ID로 개별 리포트 조회.

## 4. Runtime / Health API

### `GET /api/v1/runtime/readiness`

프론트가 앱 시작 전 준비 상태를 확인할 때 사용한다.

의도:
- `bridge ready`
- `backend ready`
- `stt ready`
를 분리해서 세션 시작 전 상태를 게이트한다.

현재 프론트 동작:
- 세션 시작 전 readiness polling
- 세션 시작 후 polling 중단
- 세션 종료 후 다시 polling 재개

### `GET /api/v1/health`

기본 health check 용도.

## 5. WebSocket API

### `WS /api/v1/ws/audio/{session_id}`

PCM 오디오 입력을 받아 발화와 이벤트를 생성한다.

쿼리:
- `input_source`

현재 사용 예:
- `system_audio`
- `mic`
- `mic_and_audio` 세션의 경우 활성 입력 소스를 반영

payload 응답:
- `session_id`
- `input_source`
- `utterances`
- `events`
- `error`

빈 payload는 보내지 않는다. 즉, `utterances` 또는 `events`가 있을 때만 전송한다.

### `WS /api/v1/ws/text/{session_id}`

텍스트 입력을 받아 발화와 이벤트를 생성한다.

용도:
- 개발용 텍스트 입력
- 오디오 없이 파이프라인 검증

## 6. 현재 운영상 중요한 정책

- 실시간 인사이트는 질문만 노출한다.
- 리포트는 자동 생성하지 않는다.
- 리포트 생성 시 세션 녹음 파일을 자동 탐색한다.
- live final이 늦으면 UI를 뒤집지 않고 저장/리포트 경로에만 반영한다.
- 리포트 산출물은 세션별 폴더에 저장한다.
