# DB 명세서

> 목적: 현재 구현된 SQLite 저장 구조와 코드 위치를 기준으로 데이터 모델을 정리한다.

---

## 1. 실제 코드 위치

| 경로 | 역할 |
|---|---|
| `backend/app/infrastructure/persistence/sqlite/database.py` | SQLite 연결 및 초기화 |
| `backend/app/infrastructure/persistence/sqlite/schema.py` | 실제 DDL |
| `backend/app/infrastructure/persistence/sqlite/repositories/` | SQLite 저장소 구현 |
| `backend/app/domain/models/` | 도메인 엔티티 |
| `backend/app/repositories/contracts/` | 저장소 인터페이스 |

---

## 2. 설계 원칙

- 회의는 `session` 단위로 관리한다.
- 발화는 `utterance` 단위로 저장한다.
- 회의 중 핵심 구조화 결과는 `overlay_events`에 저장한다.
- 화면 OCR과 현재 화면 정보는 `screen_contexts`에 저장한다.
- 회의 후 결과 문서는 `reports`에 저장한다.
- 회의 중 기능과 회의 후 기능은 같은 저장 구조를 공유한다.

---

## 3. 현재 테이블

현재 실제 스키마 기준 테이블은 아래 5개다.

- `sessions`
- `utterances`
- `screen_contexts`
- `overlay_events`
- `reports`

---

## 4. ERD

```text
sessions
  ├─ utterances
  ├─ screen_contexts
  ├─ overlay_events
  └─ reports

utterances
  └─ overlay_events.source_utterance_id

screen_contexts
  └─ overlay_events.source_screen_id
```

---

## 5. 테이블 상세

### 5.1 sessions

| 컬럼 | 타입 | 설명 |
|---|---|---|
| `id` | TEXT PK | 세션 ID |
| `title` | TEXT | 회의 제목 |
| `mode` | TEXT | `meeting`, `lecture`, `video` |
| `source` | TEXT | `mic`, `system_audio`, `file` |
| `started_at` | TEXT | 시작 시각 |
| `ended_at` | TEXT NULL | 종료 시각 |
| `status` | TEXT | `running`, `ended`, `archived` |

### 5.2 utterances

| 컬럼 | 타입 | 설명 |
|---|---|---|
| `id` | TEXT PK | 발화 ID |
| `session_id` | TEXT FK | 세션 ID |
| `seq_num` | INTEGER | 세션 내 순서 |
| `start_ms` | INTEGER | 시작 시각 |
| `end_ms` | INTEGER | 종료 시각 |
| `text` | TEXT | 발화 텍스트 |
| `confidence` | REAL | 신뢰도 |

### 5.3 screen_contexts

| 컬럼 | 타입 | 설명 |
|---|---|---|
| `id` | TEXT PK | 화면 맥락 ID |
| `session_id` | TEXT FK | 세션 ID |
| `captured_at_ms` | INTEGER | 캡처 시각 |
| `ocr_text` | TEXT NULL | OCR 원문 |
| `title_hint` | TEXT NULL | 제목 힌트 |
| `keywords_json` | TEXT NULL | 키워드 JSON |
| `image_path` | TEXT NULL | 이미지 경로 |

### 5.4 overlay_events

| 컬럼 | 타입 | 설명 |
|---|---|---|
| `id` | TEXT PK | 이벤트 ID |
| `session_id` | TEXT FK | 세션 ID |
| `source_utterance_id` | TEXT NULL | 근거 발화 |
| `source_screen_id` | TEXT NULL | 근거 화면 맥락 |
| `event_type` | TEXT | `topic`, `question`, `decision`, `action_item`, `risk`, `context` |
| `title` | TEXT | 이벤트 제목 |
| `normalized_title` | TEXT NULL | 정규화된 제목 (중복 비교용) |
| `body` | TEXT NULL | 이벤트 설명 |
| `speaker_label` | TEXT NULL | 화자 라벨 |
| `state` | TEXT | 이벤트 상태 |
| `priority` | INTEGER | 우선순위 |
| `assignee` | TEXT NULL | 담당자 |
| `due_date` | TEXT NULL | 기한 |
| `topic_group` | TEXT NULL | 주제 묶음 키 |
| `created_at_ms` | INTEGER | 생성 시각 |
| `updated_at_ms` | INTEGER | 최종 갱신 시각 |

### 5.5 reports

| 컬럼 | 타입 | 설명 |
|---|---|---|
| `id` | TEXT PK | 리포트 ID |
| `session_id` | TEXT FK | 세션 ID |
| `report_type` | TEXT | 현재는 `markdown` 중심 |
| `file_path` | TEXT | 저장 경로 |
| `generated_at` | TEXT | 생성 시각 |

---

## 6. 현재 이벤트 상태

실제 코드에서 바로 쓰는 상태는 아래 중심이다.

### topic

- `active`

### question

- `open`

### decision

- `confirmed`

### action_item

- `candidate`
- `confirmed`

### risk

- `open`

주의:
- 문서상으로 더 많은 상태 전이는 정의돼 있지만, 현재 코드에서 실제로 자동 전이되는 상태는 아직 제한적이다.

---

## 7. 현재 인덱스

실제 스키마 기준:

```sql
CREATE INDEX IF NOT EXISTS idx_utterances_session_seq
ON utterances(session_id, seq_num);

CREATE INDEX IF NOT EXISTS idx_screen_contexts_session_time
ON screen_contexts(session_id, captured_at_ms);

CREATE INDEX IF NOT EXISTS idx_overlay_events_session_type
ON overlay_events(session_id, event_type, state);
```

---

## 8. 현재 저장 흐름

### 회의 중

```text
WebSocket 입력
  -> utterances 저장
  -> analyzer 규칙 실행
  -> overlay_events 저장 또는 병합
```

### 회의 후

```text
세션 종료
  -> overlay_events 조회
  -> Markdown 리포트 생성
  -> reports 저장
```

---

## 9. 실제 구현과 문서의 경계

현재 구현됨:

- SQLite 초기화
- 세션 / 발화 / 이벤트 / 리포트 저장
- 이벤트 조회 및 병합

아직 미구현 또는 후순위:

- 마이그레이션 체계 (현재 CREATE IF NOT EXISTS 방식)
- 다중 DB 백엔드
- HTML 리포트 저장 전략
- screen_context 실제 OCR 연동

---

## 10. 요약

```text
sessions       = 회의 단위
utterances     = 발화 단위
screen_contexts = 화면 맥락 단위
overlay_events = 실시간 구조화 결과
reports        = 회의 후 산출물
```
