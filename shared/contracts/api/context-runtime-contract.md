# Context / History / Runtime Contract

이 문서는 `context`, `history timeline`, `carry-over`, `runtime readiness`, `runtime monitor` 계약을 정리한다.

## Context

- `account`
  - 회사/거래처 단위 묶음
- `contact`
  - 실제 미팅 상대
- `context_thread`
  - 같은 안건, 같은 업무 흐름

## History

### 타임라인 응답 원칙

- `timeline`은 세션과 리포트를 같이 보여준다.
- `carry_over`는 지난 회의에서 다음 회의로 이어갈 핵심만 남긴다.
- `session_count`, `report_count`는 현재 필터 기준 개수다.

### carry-over 해석

- `decisions`
  - 이미 정한 결정 사항
- `action_items`
  - 아직 처리해야 하는 액션
- `risks`
  - 추적이 필요한 리스크
- `questions`
  - 아직 덜 풀린 질문

## Runtime

### readiness

- `backend_ready`
  - 서버 프로세스 기준 준비 상태
- `warming`
  - preload 중인지 여부
- `stt_ready`
  - STT preload 완료 여부
- `preloaded_sources`
  - source별 preload 결과

### monitor

- `audio_pipeline`
  - 최근 오디오 처리 지표
- `late_final_count`
  - live에서 늦게 도착해 `late_archive_final`로 다운그레이드된 횟수
- `backpressure_count`
  - preview backpressure가 걸린 횟수
- `standalone_ratio`
  - segment 정합성이 preview 없이 standalone으로 끝난 비율
