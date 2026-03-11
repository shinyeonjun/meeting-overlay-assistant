# 환경 설정 분리 가이드

## 목적

개발 중 `.env`, 프로필 JSON, 로컬 모델 경로, 테스트용 설정이 섞이면서 경로 해석 문제가 생겼다.  
특히 `uvicorn --reload` 환경에서 stale runtime 문제가 드러났기 때문에, 로컬 경로와 운영 경로를 더 명확히 다루는 것이 중요하다.

## 현재 핵심 원칙

### 1. STT 모델 경로는 repo-local 경로를 우선한다

현재 권장 경로:

```env
STT_MODEL_PATH=backend/models/stt/faster-whisper-large-v3-turbo-ct2
```

이유:
- Hugging Face cache snapshot 경로는 불완전할 수 있다.
- repo 내부 완전 모델 디렉터리가 더 예측 가능하다.

### 2. `--reload`는 STT 검증 기준으로 쓰지 않는다

이유:
- Windows + reload 환경에서 오래된 프로세스 상태가 남아 모델 경로 해석이 꼬인 적이 있다.
- STT 모델 preload 검증은 `uvicorn backend.app.main:app` 기준이 더 안전하다.

### 3. 프로필 JSON은 명시 경로를 우선한다

`media_service_profiles.json`에서 `model_path`, `final_model_path`를 명시하면 `.env` fallback에만 의존하지 않아도 된다.

## 현재 확인된 로컬 경로

- Faster-Whisper 모델:
  - `backend/models/stt/faster-whisper-large-v3-turbo-ct2`
- Sherpa 모델:
  - `backend/models/stt/...` 계열

## 운영 시 체크 포인트

1. startup 로그에 `source=D:\\caps\\backend\\models\\...`가 찍히는지 본다.
2. `로컬 캐시를 찾지 못해 model_id로 직접 로드합니다` 경고가 없는지 본다.
3. `model_path가 유효하지 않아 무시합니다` 경고가 없는지 본다.
