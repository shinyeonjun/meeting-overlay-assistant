# 사용자 플로우 / IA 정리

이 문서는 CAPS UI를 사용자의 실제 흐름 기준으로 정리하고, 이번 차수에서 집중하는 live / note 경험 차이를 함께 설명한다.

## 핵심 사용자 질문

- 이번 회의는 어떤 맥락에서 하는가?
- 회의 중 지금 놓치면 안 되는 것은 무엇인가?
- 회의 후 바로 볼 수 있는 정리 문서는 무엇인가?
- 이전 논의와 연결되는 핵심은 무엇인가?

## 현재 핵심 플로우

### 1. 준비

- 로그인
- account / contact / thread 선택
- 참여자 입력
- carry-over / retrieval brief 확인
- 세션 생성 / 시작

### 2. 진행

- live caption 확인
- 회의 종료
- 실시간 질문/이벤트 검토는 MVP 기본 플로우에서 제외

### 3. 정리

- 세션 종료
- report generation 상태 확인
- 최신 리포트 열기
- transcript / report 확인
- 필요한 사용자에게 공유

### 4. 기록

- history timeline 조회
- carry-over 확인
- retrieval brief로 다음 회의 준비
- 공유받은 리포트 확인

## 이번 차수에서 강조하는 사용자 경험

### live 경험

- 실시간 자막은 완벽한 정답보다 빠른 표시와 안정성이 중요하다.
- 사용자는 너무 늦거나 너무 흔들리는 자막보다, 조금 덜 완벽해도 빠르게 뜨는 자막을 선호한다.
- 따라서 live STT는 partial latency와 flicker를 우선 기준으로 본다.
- MVP live 화면은 자막 중심으로 두고, 질문 카드와 실시간 이벤트 보드는 실험 기능으로 분리한다.

### note 경험

- 회의 후 노트는 실시간보다 정확도가 더 중요하다.
- 사용자는 회의가 끝난 뒤 최종 transcript와 report가 신뢰할 수 있기를 기대한다.
- 따라서 final note는 더 무거운 STT 모델과 보수적 correction을 허용한다.

### correction 경험

- 사용자는 원문이 어떻게 인식됐는지 확인할 수 있어야 한다.
- 시스템은 corrected transcript를 별도로 보관할 수 있어야 한다.
- 향후에는 반복적으로 틀리는 용어를 사용자 수정 기반 사전에 반영할 수 있어야 한다.

## IA 기준

- `준비`
- `진행`
- `정리`
- `기록`

## 화면 / 정보 구조 관점의 정리

### 준비

- 회의 맥락 입력
- 참가자 입력
- 이전 회의 맥락 확인

### 진행

- 실시간 자막
- 현재 상태 요약

### 정리

- 최종 transcript
- corrected transcript 반영 결과
- markdown / pdf report
- 공유 상태

### 기록

- 과거 회의 목록
- retrieval search
- carry-over / retrieval brief

## 현재 제외한 것

- 운영 진단 상세 지표 화면
- MVP 기본 화면의 실시간 질문 카드 / 실시간 이벤트 보드
- 감사 로그 화면
- OCR 기반 화면 컨텍스트

이 항목들은 메인 사용자 IA에서 제외한다.
