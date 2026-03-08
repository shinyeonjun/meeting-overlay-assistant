# Meeting Overlay Assistant

[![Status](https://img.shields.io/badge/status-MVP-informational)](https://github.com/shinyeonjun/meeting-overlay-assistant)
[![Backend](https://img.shields.io/badge/backend-FastAPI-009688)](https://fastapi.tiangolo.com/)
[![Frontend](https://img.shields.io/badge/frontend-Tauri%20%2B%20Vite-4F46E5)](https://tauri.app/)
[![STT](https://img.shields.io/badge/STT-Sherpa%20%2B%20Faster--Whisper-7C3AED)](https://github.com/SYSTRAN/faster-whisper)

로컬 AI 기반으로 회의 음성을 실시간 자막과 인사이트로 보조하고, 회의 종료 후 최종 리포트를 Markdown/PDF로 정리하는 회의 보조 시스템입니다.

## Preview

![오버레이 미리보기](docs/assets/overlay-preview-cropped.png)

## Overview

- 회의 중에는 `partial`/`final` 자막으로 흐름을 놓치지 않게 돕습니다.
- `question`, `decision`, `action_item`, `risk`를 실시간 이벤트로 추출합니다.
- 회의 종료 후 Markdown/PDF 리포트를 생성하고, 버전 기반으로 재생성할 수 있습니다.
- 앱 시작 시 readiness를 확인하고, 준비 완료 후에만 세션을 시작합니다.

## Service Flow

![서비스 플로우](docs/assets/system-flow.svg)

## 핵심 기능

### 실시간 회의 보조

- 입력 source: `mic`, `system_audio`, `mic_and_audio`
- 실시간 STT: `partial`/`final`
- 오버레이 UI: Tauri 기반 데스크톱 오버레이

### 인사이트 추출

- 이벤트 타입: `question`, `decision`, `action_item`, `risk`
- 이벤트 조회 / 수정 / 삭제 API 제공
- live 경로와 최종 리포트 경로를 분리하는 구조

### 리포트 생성

- Markdown / PDF 생성
- 버전 관리
- 리포트 재생성 API
- 최종 리포트 상태 조회 API

## 아키텍처

```text
Audio Input
  -> Live Capture (Tauri / Browser)
  -> STT Pipeline
      - partial: Sherpa / Web Speech API
      - final: Faster-Whisper
  -> Insight Analyzer
  -> Session Overview / Overlay
  -> Report Builder
      - Markdown
      - PDF
```

## 기술 스택

| 구분 | 스택 |
|---|---|
| Backend | Python, FastAPI, SQLite |
| Frontend | Vanilla JS, Vite, Tauri |
| STT | Web Speech API, Sherpa, Faster-Whisper |
| Analysis | Rule-based + LLM 혼합 구조 |
| Report | Markdown, PDF |

## 현재 상태

### 구현됨

- 실시간 STT 및 overview API
- 이벤트 관리 API
- Markdown/PDF 리포트 생성
- 리포트 버전 관리 및 재생성
- runtime readiness 기반 세션 시작 gating

### 진행 중

- 실시간 자막 품질 튜닝
- 오버레이 UX 개선
- final 리포트 품질 고도화

## 빠른 실행

### 백엔드

```powershell
cd D:\caps
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements-app.txt
pip install -r requirements-dev.txt
uvicorn backend.app.main:app --reload
```

### 오버레이

```powershell
cd D:\caps\frontend
npm install
npm run overlay:tauri:dev
```

## 주요 API

- `GET /api/v1/runtime/readiness`
- `POST /api/v1/sessions`
- `POST /api/v1/sessions/{session_id}/end`
- `GET /api/v1/sessions/{session_id}/overview`
- `GET /api/v1/sessions/{session_id}/events`
- `POST /api/v1/sessions/{session_id}/events/{event_id}/transition`
- `POST /api/v1/sessions/{session_id}/events/bulk-transition`
- `PATCH /api/v1/sessions/{session_id}/events/{event_id}`
- `POST /api/v1/reports/{session_id}/markdown`
- `POST /api/v1/reports/{session_id}/pdf`
- `POST /api/v1/reports/{session_id}/regenerate`

상세 스펙은 [docs/architecture/api.md](/D:/caps/docs/architecture/api.md)에서 확인할 수 있습니다.

## 저장소 구조

```text
backend/
  app/           # 실행 코드
  experiments/   # 실험 코드
  scripts/       # 실행/운영 스크립트

frontend/
  overlay/       # Tauri 오버레이 앱

docs/
  architecture/  # 아키텍처 / API / DB
  product/       # 요구사항 / 정책 / UIUX
  research/      # STT 조사 / 전략 / 벤치마크
  internal/      # 내부 메모 / 백로그 / 스프린트
```

## 문서

- 문서 인덱스: [docs/README.md](/D:/caps/docs/README.md)
- 아키텍처: [docs/architecture](/D:/caps/docs/architecture)
- 제품 문서: [docs/product](/D:/caps/docs/product)
- 연구 문서: [docs/research](/D:/caps/docs/research)
- 내부 문서: [docs/internal](/D:/caps/docs/internal)

## 로드맵

- [ ] 실시간 자막 품질 안정화
- [ ] 인사이트 precision/recall 검증 루프 구축
- [ ] PDF 리포트 레이아웃 고도화
- [ ] 오버레이 UX 마감
- [ ] 최종 데모 시나리오 정리
