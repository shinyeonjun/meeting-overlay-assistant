# Meeting Overlay Assistant

로컬 AI 기반으로 회의 음성을 실시간 분석하고, 핵심 이벤트와 후속 액션을 정리해주는 회의 보조 시스템입니다.

## 핵심 기능

- 실시간 STT (partial/final 자막)
- 질문/결정/액션/리스크 이벤트 추출
- 세션 기반 리포트 생성 (Markdown/PDF)
- Tauri 기반 오버레이 UI

## 아키텍처 흐름

```text
Audio Input (mic/system_audio)
  -> STT Pipeline
  -> Insight Analyzer
  -> Session Overview / Overlay
  -> Report Builder (Markdown/PDF)
```

## 기술 스택

- Backend: Python, FastAPI, SQLite
- STT: Web Speech API(mic), Sherpa + Faster-Whisper(system_audio)
- Frontend: Vanilla JS, Vite, Tauri
- LLM/분석: Rule-based + LLM 조합

## 빠른 실행

### 1) 백엔드

```powershell
cd D:\caps
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements-app.txt
pip install -r requirements-dev.txt
uvicorn backend.app.main:app --reload
```

### 2) 오버레이(Tauri)

```powershell
cd D:\caps\frontend
npm install
npm run overlay:tauri:dev
```

## 현재 구현 상태

- 현재 MVP 단계 개발 중
- 실시간 STT 및 이벤트 추출 기본 흐름 구현
- 리포트 생성/조회/최종 상태 조회 API 구현
- 오버레이 UX 및 인식 정확도 튜닝 진행 중

## 저장소 운영 원칙

- 실행 코드: `backend/app`, `frontend/overlay/src`
- 실험 코드: `backend/experiments`
- 내부 문서: `docs/internal`
- 로컬 산출물/캐시/모델 바이너리는 저장소 추적 제외 (`.gitignore` 반영)
- 설정은 `.env.example`만 추적

## 문서

- 전체 인덱스: [docs/README.md](/D:/caps/docs/README.md)
- 아키텍처: [docs/architecture](/D:/caps/docs/architecture)
- 제품 명세: [docs/product](/D:/caps/docs/product)
- STT 연구: [docs/research](/D:/caps/docs/research)
- 내부 운영 문서: [docs/internal](/D:/caps/docs/internal)
