# API 및 이벤트 스펙

> 목적: 현재 구현된 백엔드 기준으로 HTTP API, WebSocket, 내부 이벤트 흐름을 정리한다.  
> 최종 갱신: 2026-03-06

---

## 1. 현재 구현 상태

현재 구현된 외부 인터페이스는 아래와 같다.

- `GET /health`
- `POST /api/v1/sessions`
- `POST /api/v1/sessions/{session_id}/end`
- `GET /api/v1/sessions/{session_id}/overview`
- `POST /api/v1/reports/{session_id}/markdown`
- `POST /api/v1/reports/{session_id}/pdf`
- `GET /api/v1/reports/{session_id}`
- `GET /api/v1/reports/{session_id}/latest`
- `GET /api/v1/reports/{session_id}/final-status`
- `GET /api/v1/reports/{session_id}/{report_id}`
- `WS /api/v1/ws/audio/{session_id}`
- `WS /api/v1/ws/dev-text/{session_id}`

주의:
- 오디오 WebSocket은 PCM 바이트를 받는다.
- 개발용 텍스트 WebSocket은 UTF-8 텍스트 라인을 받는다.
- `mic`는 Web Speech API가 기본 경로이며, 실패 시 backend STT로 fallback한다.

---

## 2. 실제 코드 위치

| 경로 | 역할 |
|---|---|
| `backend/app/api/http/routes/health.py` | 헬스 체크 |
| `backend/app/api/http/routes/sessions.py` | 세션 생성, 종료, overview 조회 |
| `backend/app/api/http/routes/reports.py` | 리포트 생성/조회/final-status |
| `backend/app/api/http/routes/audio_ws.py` | 오디오/개발 텍스트 WebSocket |
| `backend/app/api/http/schemas/session.py` | 세션 요청/응답 스키마 |
| `backend/app/api/http/schemas/overview.py` | overview 응답 스키마 |
| `backend/app/api/http/schemas/audio.py` | 오디오 스트림 응답 스키마 |
| `backend/app/api/http/schemas/event.py` | 이벤트 응답 스키마 |
| `backend/app/api/http/schemas/report.py` | 리포트 응답 스키마 |
| `backend/app/api/http/serializers/audio.py` | 오디오 응답 직렬화 |

---

## 3. REST API

### 3.1 헬스 체크

`GET /health`

응답:

```json
{
  "status": "ok"
}
```

---

### 3.2 세션 시작

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
  "started_at": "2026-03-02T12:00:00+00:00",
  "ended_at": null
}
```

---

### 3.3 세션 종료

`POST /api/v1/sessions/{session_id}/end`

응답:

```json
{
  "id": "session-xxxxxxxx",
  "title": "주간 개발 회의",
  "mode": "meeting",
  "source": "system_audio",
  "status": "ended",
  "started_at": "2026-03-02T12:00:00+00:00",
  "ended_at": "2026-03-02T12:30:00+00:00"
}
```

---

### 3.4 세션 overview 조회

`GET /api/v1/sessions/{session_id}/overview`

응답:

```json
{
  "session": {
    "id": "session-xxxxxxxx",
    "title": "주간 개발 회의",
    "mode": "meeting",
    "source": "system_audio",
    "status": "ended",
    "started_at": "2026-03-02T12:00:00+00:00",
    "ended_at": "2026-03-02T12:30:00+00:00"
  },
  "current_topic": "로그인 오류 원인을 먼저 분석해보죠.",
  "questions": [
    {
      "id": "evt-xxxxxxxx",
      "title": "이거 사파리에서만 재현되는 거 맞아요?",
      "state": "open"
    }
  ],
  "decisions": [
    {
      "id": "evt-xxxxxxxx",
      "title": "이번 배포에서는 이 수정은 제외합시다.",
      "state": "confirmed"
    }
  ],
  "action_items": [
    {
      "id": "evt-xxxxxxxx",
      "title": "민수가 금요일까지 수정안 정리해 주세요.",
      "state": "confirmed"
    }
  ],
  "risks": [
    {
      "id": "evt-xxxxxxxx",
      "title": "이 일정이면 QA가 밀려서 배포가 지연될 위험이 있어요.",
      "state": "open"
    }
  ]
}
```

---

### 3.5 Markdown 리포트 생성

`POST /api/v1/reports/{session_id}/markdown`

응답:

```json
{
  "id": "report-xxxxxxxx",
  "session_id": "session-xxxxxxxx",
  "report_type": "markdown",
  "file_path": "D:/caps/backend/data/reports/session-xxxxxxxx.md"
}
```

---

### 3.6 PDF 리포트 생성

`POST /api/v1/reports/{session_id}/pdf`

응답:

```json
{
  "id": "report-xxxxxxxx",
  "session_id": "session-xxxxxxxx",
  "report_type": "pdf",
  "file_path": "D:/caps/backend/data/reports/session-xxxxxxxx.pdf"
}
```

---

### 3.7 리포트 목록 조회

`GET /api/v1/reports/{session_id}`

응답:

```json
{
  "items": [
    {
      "id": "report-xxxxxxxx",
      "session_id": "session-xxxxxxxx",
      "report_type": "markdown",
      "file_path": "D:/caps/backend/data/reports/session-xxxxxxxx.md",
      "generated_at": "2026-03-06T01:23:45+00:00"
    }
  ]
}
```

---

### 3.8 최신 리포트 조회

`GET /api/v1/reports/{session_id}/latest`

응답:

```json
{
  "id": "report-xxxxxxxx",
  "session_id": "session-xxxxxxxx",
  "report_type": "markdown",
  "file_path": "D:/caps/backend/data/reports/session-xxxxxxxx.md",
  "generated_at": "2026-03-06T01:23:45+00:00",
  "content": "# Session Report\n..."
}
```

참고:
- `report_type`이 `pdf`이면 `content`는 `null`이다.

---

### 3.9 최종 문서 상태 조회

`GET /api/v1/reports/{session_id}/final-status`

응답:

```json
{
  "session_id": "session-xxxxxxxx",
  "status": "completed",
  "report_count": 2,
  "latest_report_id": "report-xxxxxxxx",
  "latest_report_type": "pdf",
  "latest_generated_at": "2026-03-06T01:30:00+00:00",
  "latest_file_path": "D:/caps/backend/data/reports/session-xxxxxxxx.pdf"
}
```

상태 규칙:
- `pending`: 세션 실행 중이고 생성된 리포트가 없음
- `processing`: 세션 종료 상태인데 생성된 리포트가 없음
- `completed`: 최신 리포트 파일이 존재함
- `failed`: 최신 리포트 메타데이터는 있으나 파일이 없음

---

### 3.10 리포트 단건 조회

`GET /api/v1/reports/{session_id}/{report_id}`

응답:

```json
{
  "id": "report-xxxxxxxx",
  "session_id": "session-xxxxxxxx",
  "report_type": "markdown",
  "file_path": "D:/caps/backend/data/reports/session-xxxxxxxx.md",
  "generated_at": "2026-03-06T01:23:45+00:00",
  "content": "# Session Report\n..."
}
```

---

## 4. WebSocket

### 4.1 연결

- `WS /api/v1/ws/audio/{session_id}`
- `WS /api/v1/ws/dev-text/{session_id}`

---

### 4.2 입력 형식

#### 1) 오디오 WebSocket (`/api/v1/ws/audio/{session_id}`)

PCM 오디오 스트림 경로. Tauri 셸이 `stream_live_audio_ws.py`를 통해 시스템 오디오/마이크 오디오를 캡처하여 전송한다.

```text
바이너리 PCM 16-bit LE, 16kHz, mono
```

#### 2) 개발용 텍스트 WebSocket (`/api/v1/ws/dev-text/{session_id}`)

Web Speech API 최종 문장 또는 수동 입력 텍스트를 라인 단위로 전송한다.

```text
"이번 배포에서는 이 수정은 제외합시다."
```

---

### 4.3 반환 형식

오디오/개발용 텍스트 WebSocket 모두 동일한 payload 스키마를 반환한다.

```json
{
  "session_id": "session-xxxxxxxx",
  "utterances": [
    {
      "id": "live-xxxxxxxx",
      "seq_num": 1,
      "segment_id": "seg-live-1",
      "text": "이번 배포에서는 이 수정은 제외합시다.",
      "confidence": 0.95,
      "start_ms": 1772624280949,
      "end_ms": 1772624282749,
      "is_partial": true,
      "kind": "partial",
      "revision": 3
    }
  ],
  "events": [
    {
      "id": "evt-xxxxxxxx",
      "type": "decision",
      "title": "이번 배포에서는 이 수정은 제외합시다.",
      "state": "confirmed",
      "priority": 85,
      "assignee": null,
      "due_date": null
    }
  ],
  "error": null
}
```

필드 의미:
- `is_partial=true` / `kind=partial`: 실시간 draft
- `is_partial=false` / `kind=final`: 확정 문장
- `segment_id`: partial/final 교체 단위 키
- `revision`: 같은 `segment_id` 내 partial 갱신 번호

---

### 4.4 소스별 실제 연결 시퀀스

#### A) `mic` (기본: Web Speech API)

```text
1) frontend live-connection.js
   -> openLiveSocket("dev_text")
   -> 브라우저 Web Speech API 시작

2) interim(부분결과)
   -> 프론트에서 즉시 렌더링(handlePipelinePayload 직접 호출)
   -> backend 전송 없음

3) final(확정결과)
   -> /api/v1/ws/dev-text/{session_id} 로 UTF-8 텍스트 전송
   -> backend dev_text pipeline 처리
   -> utterances/events payload 반환
```

fallback:

```text
Web Speech API 오류/미지원
  -> connectTauriLiveAudio("mic")
  -> /api/v1/ws/audio/{session_id} 경유 backend STT 처리
```

#### B) `system_audio` (로컬 하이브리드 STT)

```text
1) frontend -> connectTauriLiveAudio("system_audio")
2) Tauri/python 캡처 -> /api/v1/ws/audio/{session_id} PCM 전송
3) backend audio pipeline
   -> partial: sherpa_onnx_streaming
   -> final:   faster-whisper
4) utterances/events payload 반환
```

#### C) `mic_and_audio` (듀얼 입력)

```text
1) mic 경로(Web Speech API + /dev-text) 연결
2) 동시에 system_audio 경로(/audio PCM) 연결
3) 프론트는 두 스트림 payload를 통합 렌더링
```

관련 구현 위치:
- `frontend/overlay/src/controllers/live/live-connection.js`
- `frontend/overlay/src/services/web-speech-recognizer.js`
- `frontend/overlay/src/services/live-socket.js`
- `backend/app/api/http/routes/audio_ws.py`

---

## 5. 내부 이벤트 추출 기준

현재 규칙 기반으로 추출되는 이벤트:

- `topic`
- `question`
- `decision`
- `action_item`
- `risk`

규칙 구현 위치:

- `backend/app/services/analysis/rules/event_rules.py`
- `backend/app/services/analysis/analyzers/rule_based_meeting_analyzer.py`

추가 동작:

- 같은 질문 / 결정 / 액션 / 리스크는 중복 생성하지 않고 병합한다.
- topic은 현재 active topic 기준으로 갱신된다.

---

## 6. 실제 구현과 문서의 경계

현재 구현됨:

- 세션 생성 / 종료
- overview 조회
- Markdown/PDF 리포트 생성
- 리포트 목록 조회 / 최신 조회 / 단건 조회
- 최종 문서 상태 조회(final-status)
- PCM 오디오 WebSocket + 개발용 텍스트 WebSocket 처리
- 실제 STT 엔진 조합
  - `system_audio`: `hybrid_local_streaming` (partial=sherpa, final=faster-whisper)
  - `mic`: 기본 Web Speech API, 실패 시 `faster_whisper_streaming` fallback
  - `mic_and_audio`: mic(Web Speech) + system_audio(hybrid STT) 병행
  - moonshine / simulstreaming / sensevoice는 실험 경로 유지
- 규칙 기반 + LLM 기반 이벤트 분석
- 구조화 이벤트 저장 및 반환
- 화자 구분 (pyannote 워커)
- LLM 기반 주제 요약
- LLM 기반 리포트 리파인

아직 미구현:

- HTML 리포트 생성

---

## 7. 요약

```text
현재 API는 실시간 STT + 이벤트 분석 파이프라인까지 구현되었다.
회의 중 기능은 오디오/텍스트 WebSocket + overview 조회까지,
회의 후 기능은 Markdown/PDF 리포트 생성, 목록/최신/단건 조회,
최종 문서 상태 조회(final-status)까지 동작한다.
```
