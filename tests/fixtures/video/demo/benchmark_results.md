# CAPS 벤치마크 결과

측정일: 2026-06-09 KST  
입력 데이터: `tests/fixtures/video/demo/demo_meeting.wav`  
정답 기준: `tests/fixtures/video/demo/demo_scripts.md`  
측정 원칙: 실행 중인 프로젝트 서버는 중지하거나 재시작하지 않고, 임시 DB 데이터는 삭제했다.

## 실행 환경

| 항목 | 값 |
|---|---|
| OS | Windows |
| Live control server | `http://127.0.0.1:8011` |
| Live STT server | `http://127.0.0.1:8012` |
| STT device / compute | `cuda` / `float16` |
| STT model | `deepdml/faster-whisper-large-v3-turbo-ct2` |
| Assistant model | `caps-assistant-qwen7b` |
| Retrieval embedding | `nomic-embed-text:latest` |

서버 포트 확인 결과 `8011`, `8012`는 벤치마크 후에도 계속 LISTEN 상태였다. 노트/회의록 벤치에서 생성한 임시 세션, 지식문서, 녹음/회의록 아티팩트는 삭제 확인까지 완료했다. 챗봇 벤치는 read-only 모드로 실행했고, 실행 전후 대화/메시지/job 개수는 변하지 않았다.

## 핵심 소요 시간 요약

| 항목 | 결과 | 발표용 표현 |
|---|---:|---|
| 최종 STT 처리 | 105.006초 | 6분 25초 녹음을 약 1분 45초에 처리 |
| 노트 변환 | 579.964초 | 약 9분 40초 |
| 회의록 생성 | 455.713초 | 약 7분 36초 |
| 챗봇 답변 평균 | 34.798초 | 평균 약 35초 |
| 챗봇 답변 p50 | 25.236초 | 보통 약 25초 |
| 챗봇 답변 p90 | 55.225초 | 느린 경우 약 55초 |

## 1. Live STT 지연

측정 기준은 모델 로딩 시간이 아니라, 실제 오디오가 들어간 시점부터 자막 payload가 WebSocket으로 도착할 때까지의 지연이다. 이를 위해 runtime payload에 `source_audio_end_ms`를 추가해 오디오 타임라인 기준으로 계산했다.

### 30초 구간

| 경로 | count | avg | p50 | p90 | p95 | max |
|---|---:|---:|---:|---:|---:|---:|
| preview | 24 | 797.4ms | 905.0ms | 1178.9ms | 1302.9ms | 1369.8ms |
| live_final | 14 | 888.8ms | 973.6ms | 1302.6ms | 1346.6ms | 1354.9ms |
| archive_final | 10 | 1062.7ms | 1085.7ms | 1444.4ms | 1508.1ms | 1571.9ms |

해석: 짧은 시연 구간에서는 preview/live_final 모두 대체로 1초 안팎이라 체감 지연이 크지 않다.

### 120초 구간

| 경로 | count | avg | p50 | p90 | p95 | max |
|---|---:|---:|---:|---:|---:|---:|
| preview | 133 | 2870.1ms | 2745.5ms | 4820.3ms | 5025.4ms | 5315.7ms |
| live_final | 97 | 3237.1ms | 3315.9ms | 5054.5ms | 5187.3ms | 5420.2ms |
| archive_final | 32 | 2503.3ms | 2460.2ms | 4133.1ms | 4273.2ms | 4344.3ms |
| late_archive_final | 12 | 5072.7ms | 5092.6ms | 5515.9ms | 5568.3ms | 5615.9ms |

해석: 2분 이상 지속하면 지연이 2.7~3.3초 수준으로 누적된다. 시연은 가능하지만, 장시간 회의에서는 preview/final 처리 lane 분리, backlog 제어, 오래된 preview 폐기 정책이 필요하다.

## 2. 최종 STT 정확도와 처리 속도

전체 6분 24.7초 오디오를 GPU `float16`으로 처리했다.

| 항목 | 결과 |
|---|---:|
| 오디오 길이 | 384.685초 |
| 총 처리 시간 | 105.006초 |
| RTF | 0.273 |
| raw segment | 159 |
| kept segment | 142 |
| guard keep rate | 89.31% |
| 첫 guarded text latency | 14.319초 |
| WER | 46.31% |
| CER | 26.66% |
| RSS memory delta | 약 430.4MiB |

해석: 처리 속도는 실시간보다 충분히 빠르다. 다만 현재 정답지 기준 WER/CER는 높다. 원인은 대화체, 고유명사, 잡음/겹침, 정답지 정제 방식 차이가 섞인 것으로 보이며, 발표 자료에는 “RTF는 확보했지만 최종 텍스트 정확도는 개선 여지 있음”으로 보는 게 맞다.

## 3. Live 질문 감지

라이브 회의 중 사용자가 확인해야 할 질문을 감지하는 로직을 별도 데이터셋 36건으로 측정했다.

| 항목 | 결과 |
|---|---:|
| case count | 36 |
| exact match rate | 33.33% |
| add precision / recall / f1 | 0 / 0 / 0 |
| close precision / recall / f1 | 0 / 0 / 0 |
| 평균 latency | 2222.8ms |
| p50 latency | 863.5ms |
| p90 latency | 1638.2ms |
| error count | 2 |
| failure count | 24 |

해석: 현재 질문 감지는 실사용 품질이라고 보기 어렵다. 기능을 시연에서 강하게 강조하기보다는 MVP 보조 기능으로 두고, 규칙/모델 판단 기준과 평가 데이터부터 다시 잡는 게 맞다.

## 4. 노트 변환

동일 오디오로 노트 후처리 파이프라인을 실행했다.

| 항목 | 결과 |
|---|---:|
| 전체 실행 시간 | 579.964초 |
| 프로세스 exit code | -1073740791 |
| post-processing job | completed |
| note correction job | completed |
| transcript item count | 81 |
| event count | 26 |
| report job | null |
| final report status | pending |

### 노트 변환 텍스트 정확도

최신 `테스트` 세션의 변환된 노트 발화 80개를 정답지 `demo_scripts.md`와 비교했다. 비교 전에는 문장부호, 공백, 대소문자를 제거하고 한글/영문/숫자만 남겼다.

| 항목 | 결과 |
|---|---:|
| 정답 단어 수 | 814 |
| 변환 단어 수 | 760 |
| WER | 22.85% |
| 단어 기준 정확도 | 77.15% |
| CER | 12.99% |
| 문자 기준 정확도 | 87.01% |
| 이름/호칭/감탄사 제외 WER | 20.78% |
| 이름/호칭/감탄사 제외 단어 정확도 | 79.22% |
| 단어 치환 / 삭제 / 삽입 | 94 / 73 / 19 |
| 문자 치환 / 삭제 / 삽입 | 86 / 133 / 34 |

주요 오류 유형:

- 사람 이름과 고유명사 오류: `류천아` -> `류이찬아`, `성원아` -> `성훈아`, `삐쭈님` -> `피추님`
- 비슷한 발음의 단어 오류: `캠` -> `케미`, `안건` -> `양권`, `자존감` -> `고정감`
- 말끝/조사/짧은 감탄사 누락
- 후반부 소란 구간에서 오인식 증가

해석: 노트 변환 텍스트는 최종 STT 단독 결과보다 정확도가 좋아졌고, 회의 맥락을 파악하는 데는 쓸 수 있는 수준이다. 이름/호칭/짧은 감탄사를 제외하면 단어 기준 정확도는 약 79.22%로, 발표에서는 “의미 전달 기준 약 80%”라고 표현하는 것이 적절하다. 다만 회의록이나 챗봇이 사람 이름, 결정사항, 액션아이템을 정확히 써야 하는 경우에는 고유명사 보정과 후반부 잡음 구간 보정이 필요하다. 또한 노트 전문 지식 인덱싱 단계에서 Ollama embedding 요청 timeout이 발생했고 프로세스가 비정상 exit code로 종료됐다. 이 오류는 노트 생성 결과를 막지는 않았지만, RAG 품질과 자동 회의록 생성 흐름에는 위험하다.

## 5. 회의록 생성

노트 변환으로 생성된 임시 세션에 대해 회의록 생성 job을 별도로 실행했다.

| 항목 | 결과 |
|---|---:|
| 실행 시간 | 455.713초 |
| exit code | 0 |
| report generation job | completed |
| 생성 report count | 2 |
| Markdown report | 생성 완료 |
| PDF report | 생성 완료 |

해석: 회의록 생성 job 자체는 성공했다. 다만 노트 변환 스크립트에서는 report job이 자동으로 붙지 않았기 때문에, 실제 제품 흐름에서는 “노트 완료 후 회의록 job enqueue”가 항상 보장되는지 추가 검증해야 한다.

## 6. 챗봇/RAG

서버를 유지한 상태에서 read-only 벤치로 6개 질의를 실행했다.

| 항목 | 결과 |
|---|---:|
| case count | 6 |
| completed | 6 |
| failed | 0 |
| slow | 1 |
| 평균 응답 시간 | 34.798초 |
| p50 응답 시간 | 25.236초 |
| p90 응답 시간 | 55.225초 |
| 평균 소스 수 | 5.83 |

주요 관찰:

| 질의 | 결과 |
|---|---|
| 가장 최근 회의 | 2026-06-09 `테스트` 회의를 찾아 답변함 |
| 6월 회의 여부 | 71.264초 후 답변 생성 실패 |
| 5월 회의 개수 | 최종 결론은 1개에 가깝지만, 답변 첫 문장에 2개라고 말하는 모순 발생 |
| 최근 회의 내용 | 6월 회의 내용을 비교적 잘 요약 |
| 결정사항/다음 할 일 | 일부 무관한 `캡스톤디자인` 근거가 섞임 |
| 채널명/유튜브 | 관련 답은 했지만 5월/6월 근거가 섞임 |

해석: 챗봇은 최신 회의 검색 자체는 개선됐지만, 월/날짜 범위 질의에서 구조화 session source와 report source가 서로 충돌한다. 답변도 소스 혼합 때문에 모순이 생긴다. 다음 개선 우선순위는 모델 프롬프트보다 검색/랭킹 결과의 날짜 범위 정합성, source grouping, 같은 세션 근거 우선 사용이다.

## 결론

현재 시연에서 가장 안정적으로 보여줄 수 있는 축은 Live STT 짧은 구간, 노트 변환 결과, 회의록 생성 결과다. 최종 STT는 속도는 좋지만 정확도 개선 여지가 있고, 질문 감지와 챗봇/RAG는 아직 품질 리스크가 크다.

우선순위:

1. 챗봇/RAG의 날짜 범위 검색 정합성 수정
2. 노트 전문 embedding timeout 방지와 재시도/큐 안정화
3. 노트 완료 후 회의록 job 자동 enqueue 보장
4. Live STT 장시간 backlog 누적 완화
5. 최종 STT 정답지 기준 정확도 개선
6. Live 질문 감지 평가 기준과 로직 재설계

## 원본 결과 파일

- `temp/bench_live_source_delay_30s.json`
- `temp/bench_live_source_delay_120s.json`
- `temp/bench_demo_final_stt_gpu_float16.json`
- `temp/bench_demo_live_questions_current.json`
- `temp/bench_demo_note_report_current_stdout.txt`
- `temp/bench_demo_note_report_current_stderr.txt`
- `temp/bench_demo_note_report_current_elapsed.json`
- `temp/bench_demo_note_accuracy_current.json`
- `temp/bench_demo_note_accuracy_adjusted_current.json`
- `temp/bench_demo_report_generation_current_stdout.txt`
- `temp/bench_demo_report_generation_current_elapsed.json`
- `temp/bench_demo_assistant_chat_current.json`
