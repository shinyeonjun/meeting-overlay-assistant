# API 및 이벤트 스펙

> 목적: 현재 구현된 백엔드 기준으로 HTTP API, WebSocket, 실시간 이벤트 흐름을 정리한다.  
> 최종 갱신: 2026-03-08

---

## 1. 현재 구현 범위

- `GET /health`
- `GET /api/v1/runtime/readiness`
- `POST /api/v1/sessions`
- `POST /api/v1/sessions/{session_id}/end`
- `GET /api/v1/sessions/{session_id}/overview`
- `GET /api/v1/sessions/{session_id}/events`
- `GET /api/v1/sessions/{session_id}/events/{event_id}`
- `POST /api/v1/sessions/{session_id}/events/{event_id}/transition`
- `POST /api/v1/sessions/{session_id}/events/bulk-transition`
- `PATCH /api/v1/sessions/{session_id}/events/{event_id}`
- `DELETE /api/v1/sessions/{session_id}/events/{event_id}`
- `POST /api/v1/reports/{session_id}/markdown`
- `POST /api/v1/reports/{session_id}/pdf`
- `POST /api/v1/reports/{session_id}/regenerate`
- `GET /api/v1/reports/{session_id}`
- `GET /api/v1/reports/{session_id}/latest`
- `GET /api/v1/reports/{session_id}/final-status`
- `GET /api/v1/reports/{session_id}/{report_id}`
- `WS /api/v1/ws/audio/{session_id}`
- `WS /api/v1/ws/dev-text/{session_id}`

주의:
- `audio` WebSocket은 PCM 바이너리를 받는다.
- `dev-text` WebSocket은 UTF-8 텍스트 라인을 받는다.
- `system_audio`는 하이브리드 STT, `mic`는 Web Speech API 기본 경로를 사용한다.

---

## 2. 관련 코드 위치

| 경로 | 역할 |
|---|---|
| `backend/app/api/http/routes/health.py` | health, runtime readiness |
| `backend/app/api/http/routes/sessions.py` | 세션 생성, 종료, overview |
| `backend/app/api/http/routes/events.py` | 이벤트 조회, 수정, 삭제 |
| `backend/app/api/http/routes/reports.py` | 리포트 생성, 재생성, 조회 |
| `backend/app/api/http/routes/audio_ws.py` | audio/dev-text WebSocket |
| `backend/app/api/http/schemas/session.py` | 세션 요청/응답 스키마 |
| `backend/app/api/http/schemas/events.py` | 이벤트 API 스키마 |
| `backend/app/api/http/schemas/report.py` | 리포트 API 스키마 |
| `backend/app/api/http/schemas/audio.py` | 실시간 payload 스키마 |
| `backend/app/api/http/serializers/audio.py` | 실시간 payload 직렬화 |

---

## 3. Runtime Readiness API

### 3.1 헬스 체크

`GET /health`

```json
{
  "status": "ok"
}
```

### 3.2 런타임 준비 상태

`GET /api/v1/runtime/readiness`

예시:

```json
{
  "backend_ready": true,
  "warming": false,
  "stt_ready": true,
  "preloaded_sources": [
    "mic",
    "system_audio"
  ]
}
```

의미:
- `backend_ready`: API 서버가 응답 가능한 상태
- `warming`: preload 진행 중 여부
- `stt_ready`: STT 준비 완료 여부
- `preloaded_sources`: 미리 준비된 source 목록

프론트는 이 응답과 Tauri bridge 준비 상태를 합쳐 `ready` 상태를 만든다.

---

## 4. Sessions API

### 4.1 세션 시작

`POST /api/v1/sessions`

요청:

```json
{
  "title": "주간 개발 회의",
  "mode": "meeting",
  "source": "system_audio"
}
```

응답:

```json
{
  "id": "session-xxxxxxxx",
  "title": "주간 개발 회의",
  "mode": "meeting",
  "source": "system_audio",
  "status": "running",
  "started_at": "2026-03-08T10:00:00+09:00",
  "ended_at": null,
  "primary_input_source": "system_audio",
  "actual_active_sources": [
    "system_audio"
  ]
}
```

### 4.2 세션 종료

`POST /api/v1/sessions/{session_id}/end`

세션 종료와 함께 최종 리포트 생성 경로를 탄다.

### 4.3 세션 overview 조회

`GET /api/v1/sessions/{session_id}/overview`

예시:

```json
{
  "session": {
    "id": "session-xxxxxxxx",
    "title": "주간 개발 회의",
    "mode": "meeting",
    "source": "system_audio",
    "status": "running",
    "started_at": "2026-03-08T10:00:00+09:00",
    "ended_at": null,
    "primary_input_source": "system_audio",
    "actual_active_sources": [
      "system_audio"
    ]
  },
  "current_topic": "실시간 자막 초기 지연 보정",
  "questions": [],
  "decisions": [],
  "action_items": [],
  "risks": [],
  "metrics": {
    "recent_average_latency_ms": 3420,
    "recent_utterance_count_by_source": {
      "system_audio": 14
    },
    "insight_metrics": {
      "question": 2,
      "action_item": 1
    }
  }
}
```

---

## 5. Events API

이벤트 타입은 현재 `question`, `decision`, `action_item`, `risk` 4개로 고정한다.

### 5.1 이벤트 목록 조회

`GET /api/v1/sessions/{session_id}/events`

query:
- `event_type`
- `state`

### 5.2 이벤트 단건 조회

`GET /api/v1/sessions/{session_id}/events/{event_id}`

### 5.3 이벤트 상태 전이

`POST /api/v1/sessions/{session_id}/events/{event_id}/transition`

요청 예시:

```json
{
  "target_state": "answered",
  "evidence_text": "담당자가 답변을 완료했습니다."
}
```

### 5.4 이벤트 벌크 전이

`POST /api/v1/sessions/{session_id}/events/bulk-transition`

요청 예시:

```json
{
  "event_ids": ["evt-a", "evt-b"],
  "target_state": "confirmed",
  "assignee": "플랫폼팀",
  "due_date": "2026-03-20"
}
```

### 5.5 이벤트 수정

`PATCH /api/v1/sessions/{session_id}/events/{event_id}`

요청 예시:

```json
{
  "event_type": "action_item",
  "title": "초기 warmup grace 조정",
  "state": "confirmed",
  "assignee": "yeonjun",
  "due_date": "2026-03-10",
  "evidence_text": "첫 3개 final은 6000ms까지 live에 허용"
}
```

### 5.6 이벤트 삭제

`DELETE /api/v1/sessions/{session_id}/events/{event_id}`

### 5.5 이벤트 응답 필드

```json
{
  "id": "evt-xxxxxxxx",
  "session_id": "session-xxxxxxxx",
  "event_type": "question",
  "title": "시스템 프롬프트 제외 여부 확인 필요",
  "body": null,
  "evidence_text": "그래서 시스템 프롬프",
  "speaker_label": null,
  "state": "open",
  "priority": 70,
  "assignee": null,
  "due_date": null,
  "topic_group": null,
  "source_utterance_id": "utt-xxxxxxxx",
  "source_screen_id": null,
  "created_at_ms": 1772880229000,
  "updated_at_ms": 1772880229000,
  "input_source": "system_audio",
  "insight_scope": "live"
}
```

설명:
- `evidence_text`: 이벤트 근거 문장
- `input_source`: `mic`, `system_audio`, `mic_and_audio` 등
- `insight_scope`: `live` 또는 report용 scope
- 주요 상태값:
  - `question`: `open`, `answered`, `unresolved`, `closed`
  - `decision`: `candidate`, `confirmed`, `updated`, `closed`
  - `action_item`: `open`, `candidate`, `confirmed`, `updated`, `closed`
  - `risk`: `open`, `active`, `monitoring`, `resolved`, `closed`

---

## 6. Reports API

리포트는 버전 기반으로 저장된다. 같은 세션에서 재생성하면 `v2`, `v3`가 누적된다.

### 6.1 Markdown 리포트 생성

`POST /api/v1/reports/{session_id}/markdown`

응답 예시:

```json
{
  "id": "report-xxxxxxxx",
  "session_id": "session-xxxxxxxx",
  "report_type": "markdown",
  "version": 1,
  "file_path": "D:/caps/backend/data/reports/session-xxxxxxxx.v1.md",
  "insight_source": "high_precision_audio",
  "content": "# 회의 리포트\\n...",
  "speaker_transcript": [],
  "speaker_events": []
}
```

### 6.2 PDF 리포트 생성

`POST /api/v1/reports/{session_id}/pdf`

응답 예시:

```json
{
  "id": "report-xxxxxxxx",
  "session_id": "session-xxxxxxxx",
  "report_type": "pdf",
  "version": 1,
  "file_path": "D:/caps/backend/data/reports/session-xxxxxxxx.v1.pdf",
  "insight_source": "high_precision_audio",
  "source_markdown": "# 회의 리포트\\n..."
}
```

### 6.3 리포트 재생성

`POST /api/v1/reports/{session_id}/regenerate`

응답 예시:

```json
{
  "session_id": "session-xxxxxxxx",
  "items": [
    {
      "id": "report-markdown-v2",
      "report_type": "markdown",
      "version": 2,
      "file_path": "D:/caps/backend/data/reports/session-xxxxxxxx.v2.md",
      "insight_source": "high_precision_audio"
    },
    {
      "id": "report-pdf-v2",
      "report_type": "pdf",
      "version": 2,
      "file_path": "D:/caps/backend/data/reports/session-xxxxxxxx.v2.pdf",
      "insight_source": "high_precision_audio"
    }
  ]
}
```

### 6.4 리포트 목록 / 최신 / 단건

- `GET /api/v1/reports/{session_id}`
- `GET /api/v1/reports/{session_id}/latest`
- `GET /api/v1/reports/{session_id}/{report_id}`

공통 필드:
- `id`
- `session_id`
- `report_type`
- `version`
- `file_path`
- `insight_source`
- `generated_at`

### 6.5 최종 리포트 상태

`GET /api/v1/reports/{session_id}/final-status`

```json
{
  "session_id": "session-xxxxxxxx",
  "status": "completed",
  "report_count": 4,
  "latest_report_id": "report-pdf-v2",
  "latest_report_type": "pdf",
  "latest_generated_at": "2026-03-08T10:30:00+09:00",
  "latest_file_path": "D:/caps/backend/data/reports/session-xxxxxxxx.v2.pdf"
}
```

상태:
- `pending`
- `processing`
- `completed`
- `failed`

---

## 7. WebSocket

### 7.1 연결

- `WS /api/v1/ws/audio/{session_id}`
- `WS /api/v1/ws/dev-text/{session_id}`

### 7.2 입력 포맷

#### `audio`

```text
PCM 16-bit LE, 16kHz, mono
```

#### `dev-text`

```text
회의 중 확정된 텍스트 한 줄
```

### 7.3 실시간 payload 예시

```json
{
  "session_id": "session-xxxxxxxx",
  "input_source": "system_audio",
  "utterances": [
    {
      "id": "live-xxxxxxxx",
      "seq_num": 1,
      "segment_id": "seg-live-1",
      "text": "어떤 개발",
      "confidence": 0.7,
      "start_ms": 1772878288858,
      "end_ms": 1772878288858,
      "is_partial": true,
      "kind": "partial",
      "revision": 1,
      "input_source": "system_audio"
    }
  ],
  "events": [],
  "error": null
}
```

설명:
- `kind=partial`: 실시간 초안 자막
- `kind=final`: 확정 자막
- `segment_id`: partial/final 정합성 기준
- `revision`: 같은 partial의 갱신 번호

현재 정책:
- 늦게 도착한 final은 live UI 전송을 생략할 수 있다.
- 대신 DB와 최종 리포트 생성 경로에는 반영된다.

---

## 8. 입력 source별 실제 흐름

### 8.1 `mic`

```text
브라우저 Web Speech API
  -> interim은 프론트 임시 렌더
  -> final은 /dev-text WebSocket 전송
  -> backend 이벤트 추출 / 저장
```

fallback 시:

```text
mic
  -> /audio WebSocket
  -> backend STT
```

### 8.2 `system_audio`

```text
Tauri + Python capture
  -> /audio WebSocket
  -> partial: Sherpa
  -> final: Faster-Whisper
  -> utterances / events payload 반환
```

### 8.3 `mic_and_audio`

```text
mic(dev-text) + system_audio(audio)를 병행
```

---

## 9. 구현 메모

- 이벤트는 자동 추출 후 수동 수정 API로 보정 가능
- 리포트는 `live` 이벤트와 최종 고정밀 경로를 분리하는 방향으로 설계
- 프론트는 runtime readiness를 보고 `warming -> ready`를 표시한 뒤 세션 시작을 허용
