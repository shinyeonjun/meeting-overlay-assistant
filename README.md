# Meeting Overlay Assistant

[![Status](https://img.shields.io/badge/status-MVP-informational)](https://github.com/shinyeonjun/meeting-overlay-assistant)
[![Backend](https://img.shields.io/badge/backend-FastAPI-009688)](https://fastapi.tiangolo.com/)
[![Frontend](https://img.shields.io/badge/frontend-Tauri%20%2B%20Vite-4F46E5)](https://tauri.app/)
[![STT](https://img.shields.io/badge/STT-Sherpa%20%2B%20Faster--Whisper-7C3AED)](https://github.com/SYSTRAN/faster-whisper)

플랫폼에 종속되지 않는 회의 오버레이에서 실시간 자막과 핵심 이벤트를 보여주고, 회의 종료 후에는 Markdown/PDF 리포트까지 이어지는 로컬 AI 회의 보조 시스템입니다.

![오버레이 미리보기](docs/assets/overlay-preview-cropped.png)

## 한눈에 보기

- 실시간 partial/final 자막
- 질문, 결정, 액션 아이템 추출
- 세션/이벤트/리포트 API
- Markdown/PDF 리포트 생성
- STT 백엔드 비교 및 벤치마크

## 내가 한 것

- 오버레이 클라이언트와 FastAPI 백엔드 구조 설계
- 실시간 자막, 이벤트 추출, 세션 저장 흐름 구현
- STT 백엔드 추상화와 벤치마크 체계 정리
- 회의 종료 후 리포트 생성 파이프라인 구현

## 흐름

![시스템 흐름](docs/assets/system-flow.svg)

## 스택

- Backend: Python, FastAPI, WebSocket, SQLite
- Frontend: Tauri 2, Vite, Vanilla JavaScript
- Speech/AI: Faster-Whisper, Sherpa-ONNX, OpenAI-compatible client
- Tooling: PowerShell, pytest

## 실행

### Backend

```powershell
python -m venv .venv
.\.venv\Scripts\activate
pip install -r requirements-app.txt
uvicorn backend.app.main:app --host 127.0.0.1 --port 8000
```

### Overlay

```powershell
cd frontend
npm install
npm run overlay:tauri:dev
```

### Test

```powershell
pytest
```

## 문서 더보기

- 문서 인덱스: `docs/README.md`
- API: `docs/architecture/api.md`
- 구조: `docs/architecture/구조.md`
- DB: `docs/architecture/db.md`
- UI/UX: `docs/product/오버레이_UIUX명세.md`

## 현재 집중 중

- 리포트 분석 품질 고도화
- 이벤트 추출 정확도 개선
- 실시간 STT 지연 시간과 체감 품질 개선
