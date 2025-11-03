# 테스트 가이드

## 테스트 실행

### 전체 테스트 실행
```bash
uv run pytest
```

### 특정 테스트 파일 실행
```bash
# Supervisor Graph 테스트
uv run pytest tests/test_supervisor_graph.py

# API 엔드포인트 테스트
uv run pytest tests/test_api.py

# 설정 테스트
uv run pytest tests/test_config.py
```

### 상세 출력과 함께 실행
```bash
uv run pytest -v
```

### 특정 테스트 함수 실행
```bash
uv run pytest tests/test_api.py::test_chat_endpoint -v
```

### 커버리지와 함께 실행 (추후 추가 가능)
```bash
uv run pytest --cov=backend --cov-report=html
```

## 테스트 파일 구조

- `test_supervisor_graph.py` - Supervisor Graph 단위 테스트
  - Graph 컴파일 테스트
  - 기본 실행 테스트
  - 한국어 메시지 처리 테스트
  - 멀티턴 대화 테스트

- `test_api.py` - FastAPI 엔드포인트 통합 테스트
  - 루트 엔드포인트 테스트
  - 헬스 체크 테스트
  - 채팅 엔드포인트 테스트
  - 한국어 채팅 테스트
  - 에러 케이스 테스트

- `test_config.py` - 설정 테스트
  - SystemConfig 로드 테스트
  - 환경 변수 확인 테스트

## 서버 실행 방법

테스트 후 실제 서버를 실행하려면:

```bash
# 개발 모드 (자동 재시작)
uv run uvicorn backend.app.main:app --reload

# 프로덕션 모드
uv run uvicorn backend.app.main:app --host 0.0.0.0 --port 8000
```

## API 수동 테스트

### curl 사용
```bash
# 헬스 체크
curl http://localhost:8000/health

# 채팅 (영어)
curl -X POST "http://localhost:8000/chat" \
  -H "Content-Type: application/json" \
  -d '{"message": "Hello, how are you?"}'

# 채팅 (한국어)
curl -X POST "http://localhost:8000/chat" \
  -H "Content-Type: application/json" \
  -d '{"message": "안녕하세요!"}'
```

### httpie 사용 (선택사항)
```bash
# 설치
pip install httpie

# 사용
http POST http://localhost:8000/chat message="Hello!"
```

## 주의사항

- 테스트 실행 전 `.env` 파일에 `OPENAI_API_KEY`가 설정되어 있어야 합니다
- API 테스트는 실제 OpenAI API를 호출하므로 비용이 발생할 수 있습니다
- 비용을 줄이려면 `gpt-4o-mini` 모델을 사용하세요 (현재 설정됨)
