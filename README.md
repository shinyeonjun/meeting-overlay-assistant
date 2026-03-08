# Meeting Overlay Assistant

로컬 AI 기반으로 회의 음성을 실시간 보조 자막과 인사이트로 보여주고, 회의 종료 후 최종 리포트를 문서화하는 회의 보조 시스템입니다.

## 핵심 기능

- 실시간 STT: `partial`/`final` 자막 표시
- 회의 인사이트 추출: `question`, `decision`, `action_item`, `risk`
- 리포트 생성: Markdown/PDF 생성, 버전 관리, 재생성 API
- 오버레이 UI: Tauri 기반 실시간 회의 보조 화면

## 현재 동작 흐름

```text
앱 실행
  -> frontend / backend / STT readiness 확인
  -> ready 상태에서 세션 시작 가능
  -> 세션 시작 후에만 live audio 전송
  -> 실시간 자막 / 인사이트 표시
  -> 세션 종료
  -> 최종 리포트 생성 및 조회
```

## 기술 스택

- Backend: Python, FastAPI, SQLite
- STT:
  - `mic`: Web Speech API 기본, backend STT fallback
  - `system_audio`: Sherpa partial + Faster-Whisper final
- Frontend: Vanilla JS, Vite, Tauri
- 분석: Rule-based + LLM 혼합 구조

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

### 2) 오버레이

```powershell
cd D:\caps\frontend
npm install
npm run overlay:tauri:dev
```

## 현재 구현 상태

- MVP 개발 중
- 실시간 STT / 이벤트 추출 / overview API 구현
- 이벤트 수정 API 구현
- Markdown/PDF 리포트 생성, 버전 관리, 재생성 API 구현
- startup readiness 기반 세션 시작 gating 구현
- 정확도, UX, 성능 튜닝은 계속 진행 중

## 저장소 운영 원칙

- 실행 코드: `backend/app`, `frontend/overlay/src`
- 실험 코드: `backend/experiments`
- 내부 문서: `docs/internal`
- 로컬 산출물, DB, 모델, 로그는 Git 추적 제외
- 설정은 `.env.example`만 추적

## 문서

- 문서 인덱스: [docs/README.md](/D:/caps/docs/README.md)
- 아키텍처: [docs/architecture](/D:/caps/docs/architecture)
- 제품 문서: [docs/product](/D:/caps/docs/product)
- 연구 문서: [docs/research](/D:/caps/docs/research)
- 내부 문서: [docs/internal](/D:/caps/docs/internal)
